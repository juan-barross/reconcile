from pathlib import Path

import duckdb

from reconcile import graficos
from reconcile.formato import mes_extenso, milhoes, numero, reais
from reconcile.pontes import Respostas, camada_unica, respostas

MESES = [f"2018-{m:02d}" for m in range(1, 9)]

COLUNAS = [
    ("lojistas_contratados", "contratados", numero),
    ("lojistas_ativados", "ativados", numero),
    ("leads", "leads", numero),
    ("clientes_novos", "clientes novos", numero),
    ("pedidos_validos", "pedidos válidos", numero),
    ("receita_bruta", "receita bruta", milhoes),
    ("receita_paga", "receita paga", milhoes),
    ("ticket_medio", "ticket médio", reais),
]


def _serie(r: Respostas, area: str, pergunta: str) -> dict[str, float]:
    return {m: r[(area, pergunta, m)] for m in MESES if (area, pergunta, m) in r}


def _tabela(oficial: dict[str, dict[str, float]]) -> list[str]:
    cabecalho = "| mês | " + " | ".join(nome for _, nome, _ in COLUNAS) + " |"
    return [
        cabecalho,
        "|---|" + "---:|" * len(COLUNAS),
        *(
            f"| {mes_extenso(m)} | "
            + " | ".join(fmt(oficial[m][k]) for k, _, fmt in COLUNAS)
            + " |"
            for m in MESES
        ),
    ]


def gerar(db_path: Path, pasta: Path) -> Path:
    with duckdb.connect(str(db_path), read_only=True) as con:
        r = respostas(con)
        oficial = {m: camada_unica(con, m) for m in MESES}

    graficos.linhas_por_mes(
        {
            nome: _serie(r, area, "lojistas conquistados")
            for nome, area in [
                ("marketing", "marketing"),
                ("vendas", "vendas"),
                ("operação", "operacao"),
            ]
        },
        "Lojistas conquistados por mês, segundo cada área",
        "o número de vendas é o oficial: lojistas contratados, pela data do contrato",
        numero,
        pasta / "img" / "painel_lojistas.png",
    )
    graficos.linhas_por_mes(
        {
            "vendas": _serie(r, "vendas", "receita"),
            "financeiro": _serie(r, "financeiro", "receita"),
            "oficial": {m: oficial[m]["receita_bruta"] for m in MESES},
        },
        "Receita por mês, segundo cada área e pela camada única",
        "oficial: itens + frete de pedidos válidos, pela data da compra",
        lambda v: milhoes(v, 2),
        pasta / "img" / "painel_receita.png",
    )

    texto = [
        "# Painel",
        "",
        "Gerado por `reconcile painel` a partir dos marts. Não edite os números à mão.",
        "",
        "Cada número desta página vem da camada única, com as regras do "
        "[contrato de métricas](contrato_de_metricas.md). Os gráficos mostram, ao lado, o que "
        "cada área responderia sozinha.",
        "",
        "![Lojistas por área](img/painel_lojistas.png)",
        "",
        "![Receita por área](img/painel_receita.png)",
        "",
        "## As métricas do contrato, mês a mês",
        "",
        *_tabela(oficial),
        "",
        "Setembro e outubro de 2018 ficam de fora: a base tem 20 pedidos nesses meses.",
        "",
    ]
    saida = pasta / "painel.md"
    saida.write_text("\n".join(texto), encoding="utf-8", newline="\n")
    return saida
