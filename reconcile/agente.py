import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

import duckdb

from reconcile.pontes import camada_unica

OPENROUTER = os.environ.get("OPENROUTER_API_KEY")
MODELO = os.environ.get(
    "RECONCILE_MODELO", "anthropic/claude-opus-5.5" if OPENROUTER else "claude-opus-5-5"
)
MAX_VOLTAS = 8
MAX_LINHAS = 50

SISTEMA = (
    "Você responde perguntas de negócio sobre a Olist, um marketplace brasileiro, usando as "
    "ferramentas disponíveis. Termine sempre com uma linha no formato 'RESPOSTA: <número>', "
    "sem separador de milhar e com ponto como separador decimal."
)

DEFINICOES = {
    "leads": "leads qualificados pela data do primeiro contato",
    "lojistas_contratados": "lojistas que assinaram contrato, pela data do contrato",
    "lojistas_ativados": "lojistas contratados que fizeram a primeira venda válida no mês",
    "pedidos_validos": "pedidos não cancelados, não indisponíveis e com item, pela data da compra",
    "clientes_novos": "pessoas (customer_unique_id) com a primeira compra válida no mês",
    "receita_bruta": "itens + frete de pedidos válidos, pela data da compra, em reais",
    "receita_paga": "pagamentos de pedidos válidos, pela data de aprovação, em reais",
    "ticket_medio": "receita bruta dividida por pedidos válidos, em reais",
}

FERRAMENTAS = {
    "A": {
        "name": "sql",
        "description": "Executa uma consulta SQL (DuckDB) de leitura nas tabelas do esquema raw, "
        "que guardam os CSVs da Olist como texto: raw.orders, raw.order_items, "
        "raw.order_payments, raw.customers, raw.sellers, raw.products, raw.order_reviews, "
        "raw.marketing_qualified_leads, raw.closed_deals.",
        "input_schema": {
            "type": "object",
            "properties": {"consulta": {"type": "string"}},
            "required": ["consulta"],
            "additionalProperties": False,
        },
    },
    "B": {
        "name": "metrica",
        "description": "Devolve o valor oficial de uma métrica do contrato num mês. Métricas: "
        + "; ".join(f"{k}: {v}" for k, v in DEFINICOES.items())
        + ".",
        "input_schema": {
            "type": "object",
            "properties": {
                "metrica": {"type": "string", "enum": list(DEFINICOES)},
                "mes": {"type": "string", "pattern": "^\\d{4}-\\d{2}$"},
            },
            "required": ["metrica", "mes"],
            "additionalProperties": False,
        },
    },
}


@dataclass(frozen=True)
class Resposta:
    texto: str
    valor: float | None
    tokens_entrada: int
    tokens_saida: int


def extrair_valor(texto: str) -> float | None:
    achado = re.search(r"RESPOSTA:\s*(-?\d+(?:\.\d+)?)", texto)
    return float(achado.group(1)) if achado else None


def _sql(con: duckdb.DuckDBPyConnection, consulta: str) -> str:
    if re.search(r"\b(staging|intermediate|marts)\.", consulta, re.IGNORECASE):
        return "erro: só o esquema raw está disponível"
    linhas = con.execute(consulta).fetchmany(MAX_LINHAS)
    return json.dumps(linhas, default=str, ensure_ascii=False)


def executar(versao: str, entrada: dict, db_path: Path) -> str:
    with duckdb.connect(str(db_path), read_only=True) as con:
        try:
            if versao == "A":
                return _sql(con, entrada["consulta"])
            return json.dumps(camada_unica(con, entrada["mes"])[entrada["metrica"]])
        except (duckdb.Error, KeyError) as erro:
            return f"erro: {erro}"


def _cliente():
    import anthropic

    if OPENROUTER:
        return anthropic.Anthropic(base_url="https://openrouter.ai/api", auth_token=OPENROUTER)
    return anthropic.Anthropic()


def perguntar(pergunta: str, versao: str, db_path: Path, cliente=None) -> Resposta:
    cliente = cliente or _cliente()
    mensagens = [{"role": "user", "content": pergunta}]
    entrada = saida = 0
    for _ in range(MAX_VOLTAS):
        r = cliente.messages.create(
            model=MODELO,
            max_tokens=4096,
            system=SISTEMA,
            tools=[FERRAMENTAS[versao]],
            messages=mensagens,
            output_config={"effort": "low"},
        )
        entrada, saida = entrada + r.usage.input_tokens, saida + r.usage.output_tokens
        if r.stop_reason != "tool_use":
            texto = "".join(b.text for b in r.content if b.type == "text")
            return Resposta(texto, extrair_valor(texto), entrada, saida)
        mensagens.append({"role": "assistant", "content": r.content})
        resultados = [
            {
                "type": "tool_result",
                "tool_use_id": b.id,
                "content": executar(versao, b.input, db_path),
            }
            for b in r.content
            if b.type == "tool_use"
        ]
        mensagens.append({"role": "user", "content": resultados})
    return Resposta("", None, entrada, saida)
