import pytest

from reconcile import base


@pytest.mark.parametrize(
    ("valor", "casas", "esperado"),
    [(1234567, 0, "1.234.567"), (1234.5, 2, "1.234,50"), (0, 0, "0"), (None, 0, "—")],
)
def test_numero(valor, casas, esperado):
    assert base.numero(valor, casas) == esperado


@pytest.mark.parametrize(
    ("valor", "sinal", "esperado"),
    [
        (1152656.99, False, "R$ 1.152.656,99"),
        (-10, False, "−R$ 10,00"),
        (10, True, "+ R$ 10,00"),
        (-10, True, "− R$ 10,00"),
        (None, False, "—"),
    ],
)
def test_reais(valor, sinal, esperado):
    assert base.reais(valor, sinal=sinal) == esperado


def test_pct_milhoes_e_mes():
    assert base.pct(0.1215) == "12,2%"
    assert base.pct(0.51, 0) == "51%"
    assert base.milhoes(1152656.99, 2) == "R$ 1,15 mi"
    assert base.mes_extenso("2018-03") == "mar/2018"


def test_tabela_alinha_e_aceita_cabecalho_vazio():
    texto = base.tabela(["", "R$"], [["vendas", "10"]])
    assert texto.splitlines() == ["| | R$ |", "|---|---:|", "| vendas | 10 |"]
    assert base.tabela(["a", "b", "c"], [], "lrl").splitlines()[1] == "|---|---:|---|"


def test_escrever_preenche_o_modelo(tmp_path):
    saida = base.escrever(tmp_path / "p.md", "painel", tabela="TABELA")
    texto = saida.read_text(encoding="utf-8")
    assert "TABELA" in texto and "{" not in texto


def test_cada_consulta_e_cada_yaml_carregam():
    nomes = [p.stem for p in (base.PACOTE / "sql").glob("*.sql")]
    assert {"camada_unica", "ponte_receita", "ativacao"} <= set(nomes)
    assert all(base.sql(n).strip() for n in nomes)
    assert len(base.dados("auditoria")) == 26
    assert base.dados("quebras")[0]["nome"] == "controle"
