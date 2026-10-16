import duckdb

from reconcile import base
from reconcile.caminhos import RAIZ

AREAS = ("marketing", "vendas", "financeiro", "operacao")
COMPONENTES_RECEITA = [
    ("pedidos sem data de aprovação", "sem_aprovacao", -1),
    ("pedidos aprovados sem pagamento registrado", "sem_pagamento", -1),
    ("pagamentos de pedidos sem item", "pago_sem_item", 1),
    ("pago acima de itens + frete (em geral juros)", "pago_a_mais", 1),
    ("pago abaixo de itens + frete", "pago_a_menos", 1),
    ("data de aprovação em outro mês", "efeito_data", 1),
]

Respostas = dict[tuple[str, str, str], float]


def respostas(con: duckdb.DuckDBPyConnection) -> Respostas:
    consultas = [(RAIZ / "departamentos" / f"{a}.sql").read_text(encoding="utf-8") for a in AREAS]
    return {(a, p, m): float(v) for q in consultas for a, p, m, v in con.execute(q).fetchall()}


def total(r: Respostas, area: str, pergunta: str, mes: str | None = None) -> float | None:
    valores = [v for (a, p, m), v in r.items() if (a, p) == (area, pergunta) and mes in (None, m)]
    return sum(valores) if valores else None


def ponte_receita(con: duckdb.DuckDBPyConnection, mes: str | None = None) -> dict:
    p = base.linha(con, "ponte_receita", mes=mes)
    return p | {"efeito_data": p["financeiro"] - p["financeiro_pela_compra"]}


def componentes(p: dict) -> list[tuple[str, float]]:
    return [(nome, sinal * p[chave]) for nome, chave, sinal in COMPONENTES_RECEITA]


def fecha_receita(p: dict) -> bool:
    return abs(p["vendas"] + sum(v for _, v in componentes(p)) - p["financeiro"]) < 0.005


def ponte_lojistas(con: duckdb.DuckDBPyConnection) -> dict:
    return base.linha(con, "ponte_lojistas")


def ponte_lojistas_mes(con: duckdb.DuckDBPyConnection, mes: str) -> dict:
    return base.linha(con, "ponte_lojistas_mes", mes=mes)


def fecha_lojistas(p: dict) -> bool:
    vendas = p["marketing"] - p["contato_fechou_em_outro"] + p["fechou_contato_em_outro"]
    operacao = (
        p["vendas"]
        - p["fechou_nunca_vendeu"]
        - p["fechou_vendeu_depois"]
        + p["fechou_antes_vendeu_no_mes"]
    )
    return (vendas, operacao) == (p["vendas"], p["operacao"])


def ponte_clientes(con: duckdb.DuckDBPyConnection) -> dict:
    return base.linha(con, "ponte_clientes")


def camada_unica(con: duckdb.DuckDBPyConnection, mes: str) -> dict:
    return base.linha(con, "camada_unica", mes=mes)
