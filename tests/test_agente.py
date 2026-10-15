import json
from types import SimpleNamespace as Bloco

import duckdb
import pytest

from reconcile import agente, avaliacao
from reconcile.pontes import camada_unica


class ClienteFalso:
    def __init__(self, entrada_para):
        self.entrada_para = entrada_para
        self.messages = self

    def create(self, messages, **_):
        uso = Bloco(input_tokens=10, output_tokens=5)
        ultimo = messages[-1]["content"]
        if isinstance(ultimo, list):
            resultado = json.loads(ultimo[0]["content"])
            valor = resultado[0][0] if isinstance(resultado, list) else resultado
            texto = Bloco(type="text", text=f"RESPOSTA: {valor}")
            return Bloco(stop_reason="end_turn", usage=uso, content=[texto])
        chamada = Bloco(type="tool_use", id="t1", name="f", input=self.entrada_para(ultimo))
        return Bloco(stop_reason="tool_use", usage=uso, content=[chamada])


@pytest.fixture(scope="module")
def perguntas(db_amostra_staging, tmp_path_factory):
    arquivo = tmp_path_factory.mktemp("avaliacao") / "perguntas.jsonl"
    return avaliacao.carregar_perguntas(avaliacao.gerar_perguntas(db_amostra_staging, arquivo))


def test_versao_b_responde_pela_camada_unica(db_amostra_staging):
    cliente = ClienteFalso(lambda _: {"metrica": "lojistas_contratados", "mes": "2018-01"})
    resposta = agente.perguntar("Quantos lojistas?", "B", db_amostra_staging, cliente)
    with duckdb.connect(str(db_amostra_staging), read_only=True) as con:
        assert resposta.valor == camada_unica(con, "2018-01")["lojistas_contratados"]
    assert (resposta.tokens_entrada, resposta.tokens_saida) == (20, 10)


def test_versao_a_so_enxerga_o_raw(db_amostra_staging):
    def sql(consulta):
        return agente.executar("A", {"consulta": consulta}, db_amostra_staging)

    assert sql("select 1 from marts.fct_pedidos").startswith("erro")
    assert sql("select count(*) from raw.orders") == "[[30]]"


def test_extrai_o_valor_e_julga_a_consistencia():
    assert agente.extrair_valor("calculei...\nRESPOSTA: 1152656.99") == 1152656.99
    assert agente.extrair_valor("não sei") is None
    assert avaliacao.consistente(100.4, 100) and not avaliacao.consistente(102, 100)


def test_avaliacao_compara_as_versoes(db_amostra_staging, perguntas):
    entradas = {p["pergunta"]: {"metrica": p["metrica"], "mes": p["mes"]} for p in perguntas}
    resultados = avaliacao.avaliar(
        db_amostra_staging, perguntas, versoes=("B",), cliente=ClienteFalso(entradas.get)
    )
    assert len(perguntas) == 48
    assert resultados[0].acertos() == (48, 48)
    assert "48 de 48 (100%)" in avaliacao.para_markdown(resultados, "claude-opus-5-5")
