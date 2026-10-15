import json
from dataclasses import dataclass
from pathlib import Path

import duckdb

from reconcile.agente import MODELO, Resposta, perguntar
from reconcile.caminhos import RAIZ
from reconcile.formato import numero, pct
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


def gerar_perguntas(db_path: Path, saida: Path = PERGUNTAS) -> Path:
    with duckdb.connect(str(db_path), read_only=True) as con:
        oficial = {mes: camada_unica(con, mes) for mes in MESES}
    linhas = [
        {
            "pergunta": enunciado.format(mes=f"{nome} de 2018"),
            "metrica": metrica,
            "mes": mes,
            "esperado": round(oficial[mes][metrica], 2),
        }
        for mes, nome in MESES.items()
        for metrica, enunciado in ENUNCIADOS.items()
    ]
    saida.parent.mkdir(parents=True, exist_ok=True)
    texto = "\n".join(json.dumps(linha, ensure_ascii=False) for linha in linhas) + "\n"
    saida.write_text(texto, encoding="utf-8", newline="\n")
    return saida


def carregar_perguntas(arquivo: Path = PERGUNTAS) -> list[dict]:
    return [json.loads(linha) for linha in arquivo.read_text(encoding="utf-8").splitlines()]


def consistente(valor: float | None, esperado: float) -> bool:
    return valor is not None and abs(valor - esperado) <= max(0.005 * abs(esperado), 0.5)


@dataclass(frozen=True)
class Resultado:
    versao: str
    respostas: list[tuple[dict, Resposta]]

    def acertos(self, metrica: str | None = None) -> tuple[int, int]:
        escolhidas = [(p, r) for p, r in self.respostas if metrica in (None, p["metrica"])]
        return sum(consistente(r.valor, p["esperado"]) for p, r in escolhidas), len(escolhidas)

    @property
    def tokens(self) -> tuple[int, int]:
        return (
            sum(r.tokens_entrada for _, r in self.respostas),
            sum(r.tokens_saida for _, r in self.respostas),
        )

    def custo(self, modelo: str) -> str:
        if modelo not in PRECO_POR_MILHAO:
            return "—"
        (preco_entrada, preco_saida), (entrada, saida) = PRECO_POR_MILHAO[modelo], self.tokens
        return f"US$ {numero((entrada * preco_entrada + saida * preco_saida) / 1e6, 2)}"


def avaliar(db_path: Path, perguntas: list[dict], versoes=("A", "B"), cliente=None):
    return [
        Resultado(v, [(p, perguntar(p["pergunta"], v, db_path, cliente)) for p in perguntas])
        for v in versoes
    ]


def _linha_resumo(r: Resultado, modelo: str) -> str:
    certos, total = r.acertos()
    entrada, saida = r.tokens
    return (
        f"| {r.versao} | {ACESSO[r.versao]} | {certos} de {total} ({pct(certos / total, 0)}) "
        f"| {numero(entrada)} / {numero(saida)} | {r.custo(modelo)} |"
    )


def _linha_metrica(metrica: str, resultados: list[Resultado]) -> str:
    celulas = ["{} de {}".format(*r.acertos(metrica)) for r in resultados]
    return f"| {metrica} | " + " | ".join(celulas) + " |"


def para_markdown(resultados: list[Resultado], modelo: str) -> str:
    versoes = [r.versao for r in resultados]
    linhas = [
        "# O agente contra o painel",
        "",
        f"Gerado por `reconcile avaliar` com `{modelo}`. Não edite os números à mão.",
        "",
        f"As mesmas {len(resultados[0].respostas)} perguntas de negócio foram feitas às duas "
        "versões do agente. Uma resposta é consistente quando fica a menos de 0,5% do número "
        "da camada única, o mesmo do [painel](painel.md).",
        "",
        "| versão | acesso | consistentes | tokens (entrada / saída) | custo |",
        "|---|---|---:|---:|---:|",
        *(_linha_resumo(r, modelo) for r in resultados),
        "",
        "## Por métrica",
        "",
        "| métrica | " + " | ".join(versoes) + " |",
        "|---|" + "---:|" * len(versoes),
        *(_linha_metrica(m, resultados) for m in ENUNCIADOS),
        "",
    ]
    return "\n".join(linhas)


def gerar_relatorio(db_path: Path, saida: Path, cliente=None) -> Path:
    resultados = avaliar(db_path, carregar_perguntas(), cliente=cliente)
    saida.write_text(para_markdown(resultados, MODELO), encoding="utf-8", newline="\n")
    return saida
