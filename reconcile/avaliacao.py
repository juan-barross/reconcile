import json
from pathlib import Path

from reconcile import base
from reconcile.agente import MODELO, perguntar
from reconcile.caminhos import RAIZ
from reconcile.pontes import camada_unica

PERGUNTAS = RAIZ / "avaliacao" / "perguntas.jsonl"
MESES = {
    "2018-01": "janeiro",
    "2018-02": "fevereiro",
    "2018-03": "março",
    "2018-04": "abril",
    "2018-05": "maio",
    "2018-06": "junho",
}
ENUNCIADOS = {
    "leads": "Quantos leads chegaram em {mes}?",
    "lojistas_contratados": "Quantos lojistas a Olist conquistou em {mes}?",
    "lojistas_ativados": "Quantos lojistas começaram a vender em {mes}?",
    "pedidos_validos": "Quantos pedidos a Olist teve em {mes}?",
    "clientes_novos": "Quantos clientes novos a Olist teve em {mes}?",
    "receita_bruta": "Qual foi a receita de vendas em {mes}?",
    "receita_paga": "Quanto a Olist recebeu em pagamentos em {mes}?",
    "ticket_medio": "Qual foi o ticket médio em {mes}?",
}
PRECO_POR_MILHAO = {
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-haiku-4-5": (1.0, 5.0),
}
ACESSO = {"A": "SQL nas tabelas brutas (raw)", "B": "só as métricas do contrato"}
CABECALHO = ["versão", "acesso", "consistentes", "tokens (entrada / saída)", "custo"]


def gerar_perguntas(db_path: Path, saida: Path = PERGUNTAS) -> Path:
    with base.ler(db_path) as con:
        oficial = {mes: camada_unica(con, mes) for mes in MESES}
    perguntas = [
        {
            "pergunta": texto.format(mes=f"{nome} de 2018"),
            "metrica": metrica,
            "mes": mes,
            "esperado": round(oficial[mes][metrica], 2),
        }
        for mes, nome in MESES.items()
        for metrica, texto in ENUNCIADOS.items()
    ]
    saida.parent.mkdir(parents=True, exist_ok=True)
    linhas = (json.dumps(p, ensure_ascii=False) for p in perguntas)
    saida.write_text("\n".join(linhas) + "\n", encoding="utf-8", newline="\n")
    return saida


def carregar_perguntas(arquivo: Path = PERGUNTAS) -> list[dict]:
    return [json.loads(linha) for linha in arquivo.read_text(encoding="utf-8").splitlines()]


def consistente(valor: float | None, esperado: float) -> bool:
    return valor is not None and abs(valor - esperado) <= max(0.005 * abs(esperado), 0.5)


def avaliar(db_path: Path, perguntas: list[dict], versoes=("A", "B"), cliente=None) -> dict:
    return {
        v: [(p, perguntar(p["pergunta"], v, db_path, cliente)) for p in perguntas] for v in versoes
    }


def acertos(respostas: list, metrica: str | None = None) -> tuple[int, int]:
    escolhidas = [(p, r) for p, r in respostas if metrica in (None, p["metrica"])]
    return sum(consistente(r.valor, p["esperado"]) for p, r in escolhidas), len(escolhidas)


def _resumo(versao: str, respostas: list, modelo: str) -> list[str]:
    certos, total = acertos(respostas)
    entrada = sum(r.tokens_entrada for _, r in respostas)
    saida = sum(r.tokens_saida for _, r in respostas)
    custo = base.TRACO
    if modelo in PRECO_POR_MILHAO:
        preco_entrada, preco_saida = PRECO_POR_MILHAO[modelo]
        custo = f"US$ {base.numero((entrada * preco_entrada + saida * preco_saida) / 1e6, 2)}"
    return [
        versao,
        ACESSO[versao],
        f"{certos} de {total} ({base.pct(certos / total, 0)})",
        f"{base.numero(entrada)} / {base.numero(saida)}",
        custo,
    ]


def para_markdown(resultados: dict, modelo: str, saida: Path) -> Path:
    resumo = [_resumo(v, respostas, modelo) for v, respostas in resultados.items()]
    por_metrica = [
        [m, *("{} de {}".format(*acertos(r, m)) for r in resultados.values())] for m in ENUNCIADOS
    ]
    return base.escrever(
        saida,
        "agente",
        modelo=modelo,
        n=len(next(iter(resultados.values()))),
        resumo=base.tabela(CABECALHO, resumo, "llrrr"),
        por_metrica=base.tabela(["métrica", *resultados], por_metrica),
    )


def gerar_relatorio(db_path: Path, saida: Path, cliente=None) -> Path:
    return para_markdown(avaliar(db_path, carregar_perguntas(), cliente=cliente), MODELO, saida)
