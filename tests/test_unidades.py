import pytest

from reconcile import agente, avaliacao, pontes, quebras


def test_ponte_de_receita_fecha_quando_os_componentes_somam():
    p = dict.fromkeys(["sem_aprovacao", "sem_pagamento", "pago_a_menos", "efeito_data"], 0.0)
    p |= {"vendas": 100.0, "pago_sem_item": 5.0, "pago_a_mais": 2.0, "financeiro": 107.0}
    assert pontes.fecha_receita(p)
    assert not pontes.fecha_receita(p | {"financeiro": 108.0})


def test_ponte_de_lojistas_fecha_nos_dois_sentidos():
    p = {
        "marketing": 10,
        "contato_fechou_em_outro": 3,
        "fechou_contato_em_outro": 1,
        "vendas": 8,
        "fechou_nunca_vendeu": 2,
        "fechou_vendeu_depois": 1,
        "fechou_antes_vendeu_no_mes": 4,
        "operacao": 9,
    }
    assert pontes.fecha_lojistas(p)
    assert not pontes.fecha_lojistas(p | {"operacao": 8})


def test_total_soma_meses_e_devolve_none_sem_resposta():
    r = {("vendas", "receita", "2018-01"): 1.0, ("vendas", "receita", "2018-02"): 2.0}
    assert pontes.total(r, "vendas", "receita") == 3.0
    assert pontes.total(r, "vendas", "receita", "2018-02") == 2.0
    assert pontes.total(r, "financeiro", "receita") is None


@pytest.mark.parametrize(
    ("texto", "valor"),
    [
        ("RESPOSTA: 147", 147.0),
        ("conta...\nRESPOSTA: 1152656.99", 1152656.99),
        ("RESPOSTA:-3.5", -3.5),
        ("RESPOSTA: 1.152.656,99", 1.152),
        ("sem número", None),
    ],
)
def test_extrai_o_valor(texto, valor):
    assert agente.extrair_valor(texto) == valor


@pytest.mark.parametrize("consulta", ["select 1 from MARTS.x", "select 1 from staging.y"])
def test_versao_a_nao_ve_alem_do_raw(consulta, db_amostra):
    assert agente.executar("A", {"consulta": consulta}, db_amostra).startswith("erro")


def test_erro_de_sql_volta_como_texto(db_amostra):
    assert agente.executar("A", {"consulta": "selec"}, db_amostra).startswith("erro")


@pytest.mark.parametrize(
    ("valor", "esperado", "ok"),
    [(100.4, 100, True), (100.6, 100, False), (0.4, 0, True), (None, 1, False)],
)
def test_consistencia(valor, esperado, ok):
    assert avaliacao.consistente(valor, esperado) is ok


@pytest.mark.parametrize("modelo", ["claude-opus-5-5", "anthropic/claude-opus-5.5"])
def test_custo_reconhece_o_nome_do_modelo_nos_dois_provedores(modelo):
    respostas = [({"metrica": "leads", "esperado": 1}, agente.Resposta("", 1, 1_000_000, 0))]
    assert avaliacao._resumo("B", respostas, modelo)[-1] == "US$ 4,00"


def test_falhas_viram_texto_da_tabela():
    assert quebras._falhas([]) == "nenhum"
    assert quebras._falhas([("a", 1), ("b", 5)]) == "`a` (1 linha)<br>`b` (5 linhas)"


def test_troca_inexistente_e_avisada(tmp_path):
    cenario = {"nome": "x", "trocas": [{"arquivo": "m.sql", "antes": "nada", "depois": ""}]}
    (tmp_path / "m.sql").write_text("select 1", encoding="utf-8")
    with pytest.raises(ValueError, match="trecho não encontrado"):
        quebras._preparar(cenario, tmp_path / "db.duckdb", tmp_path)
