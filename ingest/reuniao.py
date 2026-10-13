"""A reunião: cada área responde a mesma pergunta e cada diferença vira um número.

As respostas vêm das consultas em departamentos/, sem retoque. As pontes
abaixo decompõem a diferença entre duas respostas em causas que somam
exatamente a diferença; os testes conferem que a soma fecha.
"""

from dataclasses import dataclass
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
DEPARTAMENTOS = RAIZ / "departamentos"
AREAS = ("marketing", "vendas", "financeiro", "operacao")


def respostas(con: duckdb.DuckDBPyConnection) -> dict[tuple[str, str, str], float]:
    """(area, pergunta, mes) -> valor, rodando cada arquivo de departamentos/."""
    saida = {}
    for area in AREAS:
        sql = (DEPARTAMENTOS / f"{area}.sql").read_text(encoding="utf-8")
        for a, pergunta, mes, valor in con.execute(sql).fetchall():
            saida[(a, pergunta, mes)] = float(valor)
    return saida


def total(r: dict, area: str, pergunta: str, mes: str | None = None) -> float | None:
    vals = [v for (a, p, m), v in r.items() if a == area and p == pergunta and mes in (None, m)]
    return sum(vals) if vals else None


# --- Receita: vendas (itens + frete, data da compra) contra financeiro -------

_BASE_RECEITA = """
with itens as (
    select order_id, sum(price + freight_value) as vi
    from staging.stg_olist__order_items group by 1
),
pag as (
    select order_id, sum(payment_value) as vp, max(payment_installments) as parcelas
    from staging.stg_olist__order_payments group by 1
)
select
    o.order_id,
    o.order_status,
    strftime(o.purchased_at, '%Y-%m') as mes_compra,
    strftime(o.approved_at, '%Y-%m') as mes_aprovacao,
    o.approved_at is not null as aprovado,
    i.vi,
    p.vp,
    p.parcelas
from staging.stg_olist__orders as o
left join itens as i on o.order_id = i.order_id
left join pag as p on o.order_id = p.order_id
"""


@dataclass(frozen=True)
class PonteReceita:
    mes: str | None
    vendas: float
    sem_aprovacao: float  # itens de pedidos sem data de aprovação (saem)
    sem_pagamento: float  # itens de pedidos aprovados sem pagamento (saem)
    pago_sem_item: float  # pagamento de pedidos sem item (entram)
    pago_a_mais: float  # pagamento acima de itens + frete (entra)
    pago_a_mais_pedidos: int
    pago_a_mais_parcelados: int
    pago_a_menos: float  # pagamento abaixo de itens + frete (sai)
    pago_a_menos_pedidos: int
    efeito_data: float  # aprovação cai em outro mês que a compra
    financeiro: float
    cancelados_vendas: float  # valor de cancelados/indisponíveis dentro de vendas
    cancelados_financeiro: float

    @property
    def componentes(self) -> list[tuple[str, float]]:
        return [
            ("pedidos sem data de aprovação", -self.sem_aprovacao),
            ("pedidos aprovados sem pagamento registrado", -self.sem_pagamento),
            ("pagamentos de pedidos sem item", self.pago_sem_item),
            ("pago acima de itens + frete (em geral juros)", self.pago_a_mais),
            ("pago abaixo de itens + frete", self.pago_a_menos),
            ("data de aprovação em outro mês", self.efeito_data),
        ]

    def fecha(self, tolerancia: float = 0.005) -> bool:
        soma = self.vendas + sum(v for _, v in self.componentes)
        return abs(soma - self.financeiro) <= tolerancia


def ponte_receita(con: duckdb.DuckDBPyConnection, mes: str | None = None) -> PonteReceita:
    filtro = "where mes_compra = $mes" if mes else ""
    params = {"mes": mes} if mes else {}
    linha = con.execute(
        f"""
        with base as ({_BASE_RECEITA})
        select
            coalesce(sum(vi), 0),
            coalesce(sum(vi) filter (where not aprovado), 0),
            coalesce(sum(vi) filter (where aprovado and vp is null), 0),
            coalesce(sum(vp) filter (where aprovado and vi is null), 0),
            coalesce(sum(vp - vi) filter (where aprovado and vp > vi), 0),
            count(*) filter (where aprovado and vp > vi),
            count(*) filter (where aprovado and vp > vi and parcelas > 1),
            coalesce(sum(vp - vi) filter (where aprovado and vp < vi), 0),
            count(*) filter (where aprovado and vp < vi),
            coalesce(sum(vp) filter (where aprovado), 0),
            coalesce(sum(vi) filter (where order_status in ('canceled', 'unavailable')), 0),
            coalesce(sum(vp) filter (
                where aprovado and order_status in ('canceled', 'unavailable')), 0)
        from base {filtro}
        """,
        params,
    ).fetchone()
    (vendas, sem_aprov, sem_pag, sem_item, mais, n_mais, n_parc, menos, n_menos,
     fin_pela_compra, canc_v, canc_f) = (float(x) for x in linha)  # fmt: skip

    if mes:
        (fin_pela_aprovacao,) = con.execute(
            f"with base as ({_BASE_RECEITA}) "
            "select coalesce(sum(vp), 0) from base where aprovado and mes_aprovacao = $mes",
            params,
        ).fetchone()
        financeiro = float(fin_pela_aprovacao)
    else:
        financeiro = fin_pela_compra

    return PonteReceita(
        mes=mes,
        vendas=vendas,
        sem_aprovacao=sem_aprov,
        sem_pagamento=sem_pag,
        pago_sem_item=sem_item,
        pago_a_mais=mais,
        pago_a_mais_pedidos=int(n_mais),
        pago_a_mais_parcelados=int(n_parc),
        pago_a_menos=menos,
        pago_a_menos_pedidos=int(n_menos),
        efeito_data=financeiro - fin_pela_compra,
        financeiro=financeiro,
        cancelados_vendas=canc_v,
        cancelados_financeiro=canc_f,
    )


# --- Lojistas: marketing, vendas e operação ----------------------------------


@dataclass(frozen=True)
class PonteLojistas:
    contratos: int
    nunca_venderam: int
    fechados_depois_da_base: int
    venderam: int
    mes_contato_diferente_do_fechamento: int
    mediana_dias_contato_ate_fechamento: float


def ponte_lojistas(con: duckdb.DuckDBPyConnection) -> PonteLojistas:
    linha = con.execute(
        """
        with vendeu as (select distinct seller_id from staging.stg_olist__order_items),
        fim_da_base as (select max(purchased_at) as fim from staging.stg_olist__orders)
        select
            count(*),
            count(*) filter (where v.seller_id is null),
            count(*) filter (where v.seller_id is null and d.won_at > f.fim),
            count(*) filter (where v.seller_id is not null),
            count(*) filter (
                where date_trunc('month', m.first_contact_date) <> date_trunc('month', d.won_at)),
            median(datediff('day', m.first_contact_date, d.won_at))
        from staging.stg_olist__closed_deals as d
        inner join staging.stg_olist__marketing_qualified_leads as m on d.mql_id = m.mql_id
        left join vendeu as v on d.seller_id = v.seller_id
        cross join fim_da_base as f
        """
    ).fetchone()
    return PonteLojistas(*(int(x) for x in linha[:5]), float(linha[5]))


@dataclass(frozen=True)
class PonteLojistasMes:
    """Pontes exatas num mês: marketing -> vendas -> operação."""

    mes: str
    marketing: int
    contato_no_mes_fechou_em_outro: int  # sai de marketing
    fechou_no_mes_contato_em_outro: int  # entra em vendas
    vendas: int
    fechou_no_mes_nunca_vendeu: int  # sai
    fechou_no_mes_vendeu_em_outro_mes: int  # sai
    fechou_antes_primeira_venda_no_mes: int  # entra em operação
    operacao: int

    def fecha(self) -> bool:
        return (
            self.marketing
            - self.contato_no_mes_fechou_em_outro
            + self.fechou_no_mes_contato_em_outro
            == self.vendas
        ) and (
            self.vendas
            - self.fechou_no_mes_nunca_vendeu
            - self.fechou_no_mes_vendeu_em_outro_mes
            + self.fechou_antes_primeira_venda_no_mes
            == self.operacao
        )


def ponte_lojistas_mes(con: duckdb.DuckDBPyConnection, mes: str) -> PonteLojistasMes:
    linha = con.execute(
        """
        with primeira_venda as (
            select i.seller_id, min(o.purchased_at) as em
            from staging.stg_olist__order_items as i
            inner join staging.stg_olist__orders as o on i.order_id = o.order_id
            group by 1
        ),
        d as (
            select
                strftime(m.first_contact_date, '%Y-%m') as mes_contato,
                strftime(d.won_at, '%Y-%m') as mes_fechamento,
                strftime(v.em, '%Y-%m') as mes_primeira_venda
            from staging.stg_olist__closed_deals as d
            inner join staging.stg_olist__marketing_qualified_leads as m on d.mql_id = m.mql_id
            left join primeira_venda as v on d.seller_id = v.seller_id
        )
        select
            count(*) filter (where mes_contato = $mes),
            count(*) filter (where mes_contato = $mes and mes_fechamento <> $mes),
            count(*) filter (where mes_fechamento = $mes and mes_contato <> $mes),
            count(*) filter (where mes_fechamento = $mes),
            count(*) filter (where mes_fechamento = $mes and mes_primeira_venda is null),
            count(*) filter (where mes_fechamento = $mes and mes_primeira_venda <> $mes),
            count(*) filter (where mes_primeira_venda = $mes and mes_fechamento <> $mes),
            count(*) filter (where mes_primeira_venda = $mes)
        from d
        """,
        {"mes": mes},
    ).fetchone()
    return PonteLojistasMes(mes, *(int(x) for x in linha))


# --- Clientes: customer_id contra pessoa ------------------------------------


@dataclass(frozen=True)
class PonteClientes:
    customer_ids: int
    pessoas: int
    pessoas_que_voltaram: int

    @property
    def contados_a_mais(self) -> int:
        return self.customer_ids - self.pessoas


def ponte_clientes(con: duckdb.DuckDBPyConnection) -> PonteClientes:
    linha = con.execute(
        """
        select
            count(distinct customer_id),
            count(distinct customer_unique_id),
            (select count(*) from (
                select customer_unique_id from staging.stg_olist__customers
                group by 1 having count(*) > 1))
        from staging.stg_olist__customers
        """
    ).fetchone()
    return PonteClientes(*(int(x) for x in linha))


# --- Página ------------------------------------------------------------------

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def _mes_extenso(mes: str) -> str:
    ano, m = mes.split("-")
    return f"{MESES[int(m) - 1]}/{ano}"


def _n(x: float | None) -> str:
    return "—" if x is None else f"{x:,.0f}".replace(",", ".")


def _r(x: float | None, sinal: bool = False) -> str:
    if x is None:
        return "—"
    s = f"{abs(x):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    prefixo = ("+ " if x >= 0 else "− ") if sinal else ("−" if x < 0 else "")
    return f"{prefixo}R$ {s}"


def _pct(parte: float, todo: float) -> str:
    return f"{100 * parte / todo:.0f}%".replace(".", ",") if todo else "—"


def para_markdown(con: duckdb.DuckDBPyConnection, mes: str) -> str:
    r = respostas(con)
    loj = ponte_lojistas(con)
    cli = ponte_clientes(con)
    rec = ponte_receita(con)
    rec_mes = ponte_receita(con, mes)
    m = _mes_extenso(mes)

    def linha(pergunta: str, fmt=_n) -> str:
        vals = [fmt(total(r, a, pergunta, mes)) for a in AREAS]
        return f"| {pergunta} | " + " | ".join(vals) + " |"

    loj_mes = {a: total(r, a, "lojistas conquistados", mes) for a in AREAS}
    pl = ponte_lojistas_mes(con, mes)
    fora_do_mes = loj.mes_contato_diferente_do_fechamento

    partes = [
        "# A reunião",
        "",
        "Gerado por `reconcile reuniao` a partir das consultas em [`departamentos/`]"
        "(../departamentos/). Não edite os números à mão.",
        "",
        "Cada área da Olist respondeu às mesmas três perguntas com a consulta que faria "
        "sozinha. Nenhuma está errada no sentido técnico: todas rodam e todas contam alguma "
        "coisa real. Elas discordam porque cada uma escolheu uma chave, uma data e um filtro "
        "diferentes, sem escrever a escolha em lugar nenhum.",
        "",
        f"## A pauta: {m}",
        "",
        "| pergunta | marketing | vendas | financeiro | operação |",
        "|---|---:|---:|---:|---:|",
        linha("lojistas conquistados"),
        linha("clientes novos"),
        linha("receita", _r),
        "",
        "Um traço quer dizer que a área não responde essa pergunta.",
        "",
        "## Lojistas conquistados",
        "",
        f"Em {m}, marketing diz {_n(loj_mes['marketing'])}, vendas diz "
        f"{_n(loj_mes['vendas'])} e operação diz {_n(loj_mes['operacao'])}. No acumulado "
        f"da base, marketing e vendas empatam em {_n(loj.contratos)} e operação fica em "
        f"{_n(loj.venderam)}.",
        "",
        f"### Em {m}",
        "",
        "| | lojistas |",
        "|---|---:|",
        f"| **marketing** (mês do primeiro contato) | **{_n(pl.marketing)}** |",
        f"| contato em {m}, contrato fechado em outro mês | "
        f"− {_n(pl.contato_no_mes_fechou_em_outro)} |",
        f"| contrato fechado em {m}, contato em outro mês | "
        f"+ {_n(pl.fechou_no_mes_contato_em_outro)} |",
        f"| **vendas** (mês do fechamento) | **{_n(pl.vendas)}** |",
        f"| fechou em {m} e nunca vendeu | − {_n(pl.fechou_no_mes_nunca_vendeu)} |",
        f"| fechou em {m} e só vendeu num mês seguinte | "
        f"− {_n(pl.fechou_no_mes_vendeu_em_outro_mes)} |",
        f"| fechou antes e fez a primeira venda em {m} | "
        f"+ {_n(pl.fechou_antes_primeira_venda_no_mes)} |",
        f"| **operação** (mês da primeira venda) | **{_n(pl.operacao)}** |",
        "",
        "### Na base inteira",
        "",
        "| causa | lojistas | quem é afetado |",
        "|---|---:|---|",
        f"| primeiro contato e fechamento em meses diferentes | {_n(fora_do_mes)} "
        f"de {_n(loj.contratos)} ({_pct(fora_do_mes, loj.contratos)}) "
        "| marketing contra vendas, mês a mês |",
        f"| contrato assinado, lojista nunca vendeu | {_n(loj.nunca_venderam)} "
        f"({_pct(loj.nunca_venderam, loj.contratos)}) | vendas contra operação |",
        f"| ... dos quais fecharam depois do último pedido da base | "
        f"{_n(loj.fechados_depois_da_base)} | operação não tinha como contar |",
        "",
        f"Marketing e vendas contam os mesmos {_n(loj.contratos)} contratos, só que em meses "
        "diferentes: o marketing credita no mês em que o lead chegou e vendas no mês da "
        f"assinatura. A mediana entre um e outro é de "
        f"{_n(loj.mediana_dias_contato_ate_fechamento)} dias, o bastante para jogar metade "
        "dos contratos para o mês seguinte.",
        "",
        "Operação só conta quem vendeu, e conta no mês da primeira venda. A diferença para "
        f"vendas no acumulado é inteira de lojistas que assinaram e nunca venderam: "
        f"{_n(loj.nunca_venderam)} de {_n(loj.contratos)}.",
        "",
        "## Clientes novos",
        "",
        f"Marketing conta {_n(cli.customer_ids)} clientes e operação conta {_n(cli.pessoas)}. "
        f"A diferença, {_n(cli.contados_a_mais)}, é toda de clientes que voltaram a comprar: "
        f"a Olist cria um `customer_id` novo a cada pedido, e o marketing conta essa coluna. "
        f"São {_n(cli.pessoas_que_voltaram)} pessoas com mais de um pedido. Em {m} a "
        f"diferença é {_n(total(r, 'marketing', 'clientes novos', mes))} contra "
        f"{_n(total(r, 'operacao', 'clientes novos', mes))}, pelo mesmo motivo.",
        "",
        "| causa | clientes |",
        "|---|---:|",
        f"| pedidos de quem já tinha comprado antes, contados como cliente novo "
        f"| {_n(cli.contados_a_mais)} |",
        "",
        "## Receita",
        "",
        "Vendas soma preço dos itens mais frete, pela data da compra. Financeiro soma o que "
        "foi pago, pela data de aprovação. A ponte abaixo vai de um número ao outro; cada "
        "linha é uma causa e a soma fecha no centavo.",
        "",
        "### Na base inteira",
        "",
        _tabela_ponte(rec),
        "",
        f"A maior parcela não é juros. São {_r(rec.pago_sem_item)} pagos em pedidos que "
        "não têm nenhum item, quase todos cancelados ou indisponíveis: o financeiro viu o "
        "dinheiro entrar, vendas nunca registrou o item. O que foi pago acima de itens "
        f"+ frete soma {_r(rec.pago_a_mais)} em {_n(rec.pago_a_mais_pedidos)} pedidos, "
        f"{_n(rec.pago_a_mais_parcelados)} deles parcelados: é o juro do parcelamento.",
        "",
        f"Cancelados e indisponíveis pesam {_r(rec.cancelados_vendas)} na conta de vendas "
        f"e {_r(rec.cancelados_financeiro)} na do financeiro. Nenhuma das duas consultas "
        "olha o status do pedido.",
        "",
        f"### Em {m}",
        "",
        _tabela_ponte(rec_mes),
        "",
        "Num mês isolado aparece a causa que some no acumulado: a data. Um pedido feito no "
        "dia 31 e aprovado no dia 1º é receita de um mês para vendas e do outro para o "
        "financeiro.",
        "",
        "## O que isso pede",
        "",
        "Nenhuma das diferenças acima é erro de SQL. Todas são decisões que ninguém escreveu: "
        "qual coluna é o cliente, qual data vale, se cancelado entra. O próximo passo é "
        "escrever essas decisões num [contrato de métricas](contrato_de_metricas.md) e "
        "construir uma camada única que as aplique.",
        "",
    ]
    return "\n".join(partes)


def _tabela_ponte(p: PonteReceita) -> str:
    linhas = [
        "| | R$ |",
        "|---|---:|",
        f"| **vendas** (itens + frete, data da compra) | **{_r(p.vendas)}** |",
    ]
    linhas += [f"| {nome} | {_r(v, sinal=True)} |" for nome, v in p.componentes if v]
    linhas.append(f"| **financeiro** (pagamentos, data de aprovação) | **{_r(p.financeiro)}** |")
    return "\n".join(linhas)


def gerar(db_path: Path, saida: Path, mes: str = "2018-03") -> Path:
    with duckdb.connect(str(db_path), read_only=True) as con:
        texto = para_markdown(con, mes)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(texto, encoding="utf-8", newline="\n")
    return saida
