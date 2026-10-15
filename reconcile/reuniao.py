from pathlib import Path

import duckdb

from reconcile.formato import TRACO, mes_extenso, numero, pct, reais
from reconcile.pontes import (
    AREAS,
    PonteReceita,
    camada_unica,
    ponte_clientes,
    ponte_lojistas,
    ponte_lojistas_mes,
    ponte_receita,
    respostas,
    total,
)


def _fracao(parte: float, todo: float) -> str:
    return pct(parte / todo, casas=0) if todo else TRACO


def _tabela_ponte_receita(p: PonteReceita) -> str:
    linhas = [
        "| | R$ |",
        "|---|---:|",
        f"| **vendas** (itens + frete, data da compra) | **{reais(p.vendas)}** |",
        *(f"| {nome} | {reais(v, sinal=True)} |" for nome, v in p.componentes if v),
        f"| **financeiro** (pagamentos, data de aprovação) | **{reais(p.financeiro)}** |",
    ]
    return "\n".join(linhas)


def _tabela_camada_unica(v: dict[str, float], m: str) -> str:
    linhas = [
        f"| métrica | {m} | regra (ver contrato) |",
        "|---|---:|---|",
        f"| lojistas contratados | {numero(v['lojistas_contratados'])} | data do contrato |",
        f"| lojistas ativados | {numero(v['lojistas_ativados'])} | "
        "primeira venda válida, no mês dela |",
        f"| clientes novos | {numero(v['clientes_novos'])} | "
        "pessoa (`customer_unique_id`), primeira compra válida |",
        f"| pedidos válidos | {numero(v['pedidos_validos'])} | "
        "sem cancelados, indisponíveis ou pedidos sem item |",
        f"| receita bruta | {reais(v['receita_bruta'])} | itens + frete, data da compra |",
        f"| receita paga | {reais(v['receita_paga'])} | "
        "pagamentos, data de aprovação (reserva: compra) |",
        f"| ticket médio | {reais(v['ticket_medio'])} | receita bruta ÷ pedidos válidos |",
    ]
    return "\n".join(linhas)


def para_markdown(con: duckdb.DuckDBPyConnection, mes: str) -> str:
    r = respostas(con)
    loj = ponte_lojistas(con)
    loj_mes = ponte_lojistas_mes(con, mes)
    cli = ponte_clientes(con)
    rec = ponte_receita(con)
    m = mes_extenso(mes)
    fora_do_mes = loj.mes_contato_diferente_do_fechamento

    def linha_pauta(pergunta: str, fmt=numero) -> str:
        valores = " | ".join(fmt(total(r, area, pergunta, mes)) for area in AREAS)
        return f"| {pergunta} | {valores} |"

    def resposta(area: str, pergunta: str) -> str:
        return numero(total(r, area, pergunta, mes))

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
        linha_pauta("lojistas conquistados"),
        linha_pauta("clientes novos"),
        linha_pauta("receita", reais),
        "",
        "Um traço quer dizer que a área não responde essa pergunta.",
        "",
        "## Lojistas conquistados",
        "",
        f"Em {m}, marketing diz {resposta('marketing', 'lojistas conquistados')}, vendas diz "
        f"{resposta('vendas', 'lojistas conquistados')} e operação diz "
        f"{resposta('operacao', 'lojistas conquistados')}. No acumulado da base, marketing e "
        f"vendas empatam em {numero(loj.contratos)} e operação fica em {numero(loj.venderam)}.",
        "",
        f"### Em {m}",
        "",
        "| | lojistas |",
        "|---|---:|",
        f"| **marketing** (mês do primeiro contato) | **{numero(loj_mes.marketing)}** |",
        f"| contato em {m}, contrato fechado em outro mês | "
        f"− {numero(loj_mes.contato_no_mes_fechou_em_outro)} |",
        f"| contrato fechado em {m}, contato em outro mês | "
        f"+ {numero(loj_mes.fechou_no_mes_contato_em_outro)} |",
        f"| **vendas** (mês do fechamento) | **{numero(loj_mes.vendas)}** |",
        f"| fechou em {m} e nunca vendeu | − {numero(loj_mes.fechou_no_mes_nunca_vendeu)} |",
        f"| fechou em {m} e só vendeu num mês seguinte | "
        f"− {numero(loj_mes.fechou_no_mes_vendeu_em_outro_mes)} |",
        f"| fechou antes e fez a primeira venda em {m} | "
        f"+ {numero(loj_mes.fechou_antes_primeira_venda_no_mes)} |",
        f"| **operação** (mês da primeira venda) | **{numero(loj_mes.operacao)}** |",
        "",
        "### Na base inteira",
        "",
        "| causa | lojistas | quem é afetado |",
        "|---|---:|---|",
        f"| primeiro contato e fechamento em meses diferentes | {numero(fora_do_mes)} "
        f"de {numero(loj.contratos)} ({_fracao(fora_do_mes, loj.contratos)}) "
        "| marketing contra vendas, mês a mês |",
        f"| contrato assinado, lojista nunca vendeu | {numero(loj.nunca_venderam)} "
        f"({_fracao(loj.nunca_venderam, loj.contratos)}) | vendas contra operação |",
        f"| ... dos quais fecharam depois do último pedido da base | "
        f"{numero(loj.fechados_depois_da_base)} | operação não tinha como contar |",
        "",
        f"Marketing e vendas contam os mesmos {numero(loj.contratos)} contratos, só que em "
        "meses diferentes: o marketing credita no mês em que o lead chegou e vendas no mês da "
        "assinatura. A mediana entre um e outro é de "
        f"{numero(loj.mediana_dias_contato_ate_fechamento)} dias, o bastante para jogar metade "
        "dos contratos para o mês seguinte.",
        "",
        "Operação só conta quem vendeu, e conta no mês da primeira venda. A diferença para "
        "vendas no acumulado é inteira de lojistas que assinaram e nunca venderam: "
        f"{numero(loj.nunca_venderam)} de {numero(loj.contratos)}.",
        "",
        "## Clientes novos",
        "",
        f"Marketing conta {numero(cli.customer_ids)} clientes e operação conta "
        f"{numero(cli.pessoas)}. A diferença, {numero(cli.contados_a_mais)}, é toda de clientes "
        "que voltaram a comprar: a Olist cria um `customer_id` novo a cada pedido, e o "
        f"marketing conta essa coluna. São {numero(cli.pessoas_que_voltaram)} pessoas com mais "
        f"de um pedido. Em {m} a diferença é {resposta('marketing', 'clientes novos')} contra "
        f"{resposta('operacao', 'clientes novos')}, pelo mesmo motivo.",
        "",
        "| causa | clientes |",
        "|---|---:|",
        "| pedidos de quem já tinha comprado antes, contados como cliente novo "
        f"| {numero(cli.contados_a_mais)} |",
        "",
        "## Receita",
        "",
        "Vendas soma preço dos itens mais frete, pela data da compra. Financeiro soma o que "
        "foi pago, pela data de aprovação. A ponte abaixo vai de um número ao outro; cada "
        "linha é uma causa e a soma fecha no centavo.",
        "",
        "### Na base inteira",
        "",
        _tabela_ponte_receita(rec),
        "",
        f"A maior parcela não é juros. São {reais(rec.pago_sem_item)} pagos em pedidos que "
        "não têm nenhum item, quase todos cancelados ou indisponíveis: o financeiro viu o "
        "dinheiro entrar, vendas nunca registrou o item. O que foi pago acima de itens "
        f"+ frete soma {reais(rec.pago_a_mais)} em {numero(rec.pago_a_mais_pedidos)} pedidos, "
        f"{numero(rec.pago_a_mais_parcelados)} deles parcelados: é o juro do parcelamento.",
        "",
        f"Cancelados e indisponíveis pesam {reais(rec.cancelados_vendas)} na conta de vendas "
        f"e {reais(rec.cancelados_financeiro)} na do financeiro. Nenhuma das duas consultas "
        "olha o status do pedido.",
        "",
        f"### Em {m}",
        "",
        _tabela_ponte_receita(ponte_receita(con, mes)),
        "",
        "Num mês isolado aparece a causa que some no acumulado: a data. Um pedido feito no "
        "dia 31 e aprovado no dia 1º é receita de um mês para vendas e do outro para o "
        "financeiro.",
        "",
        "## A resposta da camada única",
        "",
        "Nenhuma das diferenças acima é erro de SQL. Todas são decisões que ninguém escreveu: "
        "qual coluna é o cliente, qual data vale, se cancelado entra. O "
        "[contrato de métricas](contrato_de_metricas.md) escreve essas decisões e os marts do "
        f"dbt as aplicam. Em {m}, a camada única responde:",
        "",
        _tabela_camada_unica(camada_unica(con, mes), m),
        "",
        "Cada área continua podendo olhar o seu recorte, mas agora com nome próprio: o "
        'marketing quer "contratos por mês do lead", que é outra pergunta, e não '
        '"lojistas conquistados" com outra data.',
        "",
    ]
    return "\n".join(partes)


def gerar(db_path: Path, saida: Path, mes: str) -> Path:
    with duckdb.connect(str(db_path), read_only=True) as con:
        texto = para_markdown(con, mes)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(texto, encoding="utf-8", newline="\n")
    return saida
