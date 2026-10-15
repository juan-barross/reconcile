from dataclasses import dataclass, fields

import duckdb

from reconcile.caminhos import RAIZ

DEPARTAMENTOS = RAIZ / "departamentos"
AREAS = ("marketing", "vendas", "financeiro", "operacao")
CANCELADO = "order_status in ('canceled', 'unavailable')"

Respostas = dict[tuple[str, str, str], float]


def respostas(con: duckdb.DuckDBPyConnection) -> Respostas:
    saida: Respostas = {}
    for area in AREAS:
        sql = (DEPARTAMENTOS / f"{area}.sql").read_text(encoding="utf-8")
        for a, pergunta, mes, valor in con.execute(sql).fetchall():
            saida[(a, pergunta, mes)] = float(valor)
    return saida


def total(r: Respostas, area: str, pergunta: str, mes: str | None = None) -> float | None:
    valores = [v for (a, p, m), v in r.items() if (a, p) == (area, pergunta) and mes in (None, m)]
    return sum(valores) if valores else None


@dataclass(frozen=True)
class PonteReceita:
    vendas: float
    sem_aprovacao: float
    sem_pagamento: float
    pago_sem_item: float
    pago_a_mais: float
    pago_a_mais_pedidos: int
    pago_a_mais_parcelados: int
    pago_a_menos: float
    pago_a_menos_pedidos: int
    financeiro_pela_compra: float
    cancelados_vendas: float
    cancelados_financeiro: float
    financeiro: float

    @property
    def efeito_data(self) -> float:
        return self.financeiro - self.financeiro_pela_compra

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


_COMPONENTES_RECEITA = [
    ("sum(vi)", "true"),
    ("sum(vi)", "not aprovado"),
    ("sum(vi)", "aprovado and vp is null"),
    ("sum(vp)", "aprovado and vi is null"),
    ("sum(vp - vi)", "aprovado and vp > vi"),
    ("count(*)", "aprovado and vp > vi"),
    ("count(*)", "aprovado and vp > vi and parcelas > 1"),
    ("sum(vp - vi)", "aprovado and vp < vi"),
    ("count(*)", "aprovado and vp < vi"),
    ("sum(vp)", "aprovado"),
    ("sum(vi)", CANCELADO),
    ("sum(vp)", f"aprovado and {CANCELADO}"),
]

_BASE_RECEITA = """
with itens as (
    select order_id, sum(price + freight_value) as vi
    from staging.stg_olist__order_items
    group by 1
),

pagamentos as (
    select order_id, sum(payment_value) as vp, max(payment_installments) as parcelas
    from staging.stg_olist__order_payments
    group by 1
)

select
    o.order_status,
    strftime(o.purchased_at, '%Y-%m') as mes_compra,
    strftime(o.approved_at, '%Y-%m') as mes_aprovacao,
    o.approved_at is not null as aprovado,
    i.vi,
    p.vp,
    p.parcelas
from staging.stg_olist__orders as o
left join itens as i on o.order_id = i.order_id
left join pagamentos as p on o.order_id = p.order_id
"""


def ponte_receita(con: duckdb.DuckDBPyConnection, mes: str | None = None) -> PonteReceita:
    no_periodo = "mes_compra = $mes" if mes else "true"
    colunas = [
        f"coalesce({agg} filter (where ({cond}) and {no_periodo}), 0)"
        for agg, cond in _COMPONENTES_RECEITA
    ]

    colunas.append(
        "coalesce(sum(vp) filter (where aprovado and mes_aprovacao = $mes), 0)"
        if mes
        else "coalesce(sum(vp) filter (where aprovado), 0)"
    )
    sql = f"with base as ({_BASE_RECEITA}) select {', '.join(colunas)} from base"
    linha = con.execute(sql, {"mes": mes} if mes else {}).fetchone()
    tipos = [f.type for f in fields(PonteReceita)]
    return PonteReceita(
        *(int(v) if t is int else float(v) for v, t in zip(linha, tipos, strict=True))
    )


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
                where date_trunc('month', m.first_contact_date) <> date_trunc('month', d.won_at)
            ),
            median(datediff('day', m.first_contact_date, d.won_at))
        from staging.stg_olist__closed_deals as d
        inner join staging.stg_olist__marketing_qualified_leads as m on d.mql_id = m.mql_id
        left join vendeu as v on d.seller_id = v.seller_id
        cross join fim_da_base as f
        """
    ).fetchone()
    return PonteLojistas(*map(int, linha[:5]), float(linha[5]))


@dataclass(frozen=True)
class PonteLojistasMes:
    mes: str
    marketing: int
    contato_no_mes_fechou_em_outro: int
    fechou_no_mes_contato_em_outro: int
    vendas: int
    fechou_no_mes_nunca_vendeu: int
    fechou_no_mes_vendeu_em_outro_mes: int
    fechou_antes_primeira_venda_no_mes: int
    operacao: int

    def fecha(self) -> bool:
        marketing_para_vendas = (
            self.marketing
            - self.contato_no_mes_fechou_em_outro
            + self.fechou_no_mes_contato_em_outro
        )
        vendas_para_operacao = (
            self.vendas
            - self.fechou_no_mes_nunca_vendeu
            - self.fechou_no_mes_vendeu_em_outro_mes
            + self.fechou_antes_primeira_venda_no_mes
        )
        return marketing_para_vendas == self.vendas and vendas_para_operacao == self.operacao


def ponte_lojistas_mes(con: duckdb.DuckDBPyConnection, mes: str) -> PonteLojistasMes:
    linha = con.execute(
        """
        with primeira_venda as (
            select i.seller_id, min(o.purchased_at) as em
            from staging.stg_olist__order_items as i
            inner join staging.stg_olist__orders as o on i.order_id = o.order_id
            group by 1
        ),

        contratos as (
            select
                strftime(m.first_contact_date, '%Y-%m') as contato,
                strftime(d.won_at, '%Y-%m') as fechamento,
                strftime(v.em, '%Y-%m') as venda
            from staging.stg_olist__closed_deals as d
            inner join staging.stg_olist__marketing_qualified_leads as m on d.mql_id = m.mql_id
            left join primeira_venda as v on d.seller_id = v.seller_id
        )

        select
            count(*) filter (where contato = $mes),
            count(*) filter (where contato = $mes and fechamento <> $mes),
            count(*) filter (where fechamento = $mes and contato <> $mes),
            count(*) filter (where fechamento = $mes),
            count(*) filter (where fechamento = $mes and venda is null),
            count(*) filter (where fechamento = $mes and venda <> $mes),
            count(*) filter (where venda = $mes and fechamento <> $mes),
            count(*) filter (where venda = $mes)
        from contratos
        """,
        {"mes": mes},
    ).fetchone()
    return PonteLojistasMes(mes, *map(int, linha))


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
        with por_pessoa as (
            select customer_unique_id, count(*) as ids
            from staging.stg_olist__customers
            group by 1
        )
        select sum(ids), count(*), count(*) filter (where ids > 1)
        from por_pessoa
        """
    ).fetchone()
    return PonteClientes(*map(int, linha))


def camada_unica(con: duckdb.DuckDBPyConnection, mes: str) -> dict[str, float]:
    linha = con.execute(
        """
        select
            (select count(*) from marts.dim_leads
             where strftime(primeiro_contato_em, '%Y-%m') = $mes),
            (select count(*) from marts.fct_jornada_lojista
             where strftime(contratado_em, '%Y-%m') = $mes),
            (select count(*) from marts.fct_jornada_lojista
             where foi_ativado and strftime(primeira_venda_em, '%Y-%m') = $mes),
            (select count(*) from marts.dim_clientes
             where strftime(primeira_compra_em, '%Y-%m') = $mes),
            (select count(*) from marts.fct_pedidos
             where eh_valido and strftime(comprado_em, '%Y-%m') = $mes),
            (select coalesce(sum(receita_bruta), 0) from marts.fct_pedidos
             where strftime(comprado_em, '%Y-%m') = $mes),
            (select coalesce(sum(receita_paga), 0) from marts.fct_pedidos
             where strftime(receita_paga_em, '%Y-%m') = $mes)
        """,
        {"mes": mes},
    ).fetchone()
    nomes = (
        "leads",
        "lojistas_contratados",
        "lojistas_ativados",
        "clientes_novos",
        "pedidos_validos",
        "receita_bruta",
        "receita_paga",
    )
    valores = {nome: float(v) for nome, v in zip(nomes, linha, strict=True)}
    pedidos = valores["pedidos_validos"]
    valores["ticket_medio"] = valores["receita_bruta"] / pedidos if pedidos else 0.0
    return valores
