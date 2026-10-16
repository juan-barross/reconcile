from pathlib import Path

from reconcile import base, graficos, pontes

MESES = [f"2018-{m:02d}" for m in range(1, 9)]
COLUNAS = {
    "lojistas_contratados": ("contratados", base.numero),
    "lojistas_ativados": ("ativados", base.numero),
    "leads": ("leads", base.numero),
    "clientes_novos": ("clientes novos", base.numero),
    "pedidos_validos": ("pedidos válidos", base.numero),
    "receita_bruta": ("receita bruta", base.milhoes),
    "receita_paga": ("receita paga", base.milhoes),
    "ticket_medio": ("ticket médio", base.reais),
}
LOJISTAS = {"marketing": "marketing", "vendas": "vendas", "operação": "operacao"}


def gerar(db_path: Path, pasta: Path) -> Path:
    with base.ler(db_path) as con:
        r = pontes.respostas(con)
        oficial = {m: pontes.camada_unica(con, m) for m in MESES}

    def serie(area: str, pergunta: str) -> dict[str, float]:
        return {m: r[(area, pergunta, m)] for m in MESES if (area, pergunta, m) in r}

    lojistas = {nome: serie(area, "lojistas conquistados") for nome, area in LOJISTAS.items()}
    receita = {
        "vendas": serie("vendas", "receita"),
        "financeiro": serie("financeiro", "receita"),
        "oficial": {m: oficial[m]["receita_bruta"] for m in MESES},
    }
    graficos.linhas_por_mes(
        lojistas,
        "Lojistas conquistados por mês, segundo cada área",
        "o número de vendas é o oficial: lojistas contratados, pela data do contrato",
        base.numero,
        pasta / "img" / "painel_lojistas.png",
    )
    graficos.linhas_por_mes(
        receita,
        "Receita por mês, segundo cada área e pela camada única",
        "oficial: itens + frete de pedidos válidos, pela data da compra",
        lambda v: base.milhoes(v, 2),
        pasta / "img" / "painel_receita.png",
    )
    corpo = [
        [base.mes_extenso(m), *(fmt(oficial[m][k]) for k, (_, fmt) in COLUNAS.items())]
        for m in MESES
    ]
    cabecalho = ["mês", *(nome for nome, _ in COLUNAS.values())]
    return base.escrever(pasta / "painel.md", "painel", tabela=base.tabela(cabecalho, corpo))
