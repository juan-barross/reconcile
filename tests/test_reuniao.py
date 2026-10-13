import duckdb
import pytest

from ingest import reuniao


@pytest.fixture
def con(db_amostra_staging):
    with duckdb.connect(str(db_amostra_staging), read_only=True) as c:
        yield c


def _meses(con):
    return [m for (m,) in con.execute(
        "select distinct strftime(purchased_at, '%Y-%m') from staging.stg_olist__orders order by 1"
    ).fetchall()]  # fmt: skip


def test_ponte_de_receita_fecha_na_base_e_em_cada_mes(con):
    assert reuniao.ponte_receita(con).fecha()
    for mes in _meses(con):
        assert reuniao.ponte_receita(con, mes).fecha(), mes


def test_ponte_de_receita_acha_as_causas_plantadas(con):
    p = reuniao.ponte_receita(con)
    assert p.pago_a_mais_pedidos == 3  # o05, o10, o15 com juros de 2%
    assert p.pago_a_mais_parcelados == 3
    assert p.pago_sem_item == pytest.approx(160.0)  # o29 e o30, R$ 80 cada
    assert p.sem_pagamento == pytest.approx(20.0)  # o07: R$ 15 + R$ 5 de frete
    assert p.pago_a_menos == 0


def test_ponte_de_receita_bate_com_as_consultas_das_areas(con):
    r = reuniao.respostas(con)
    p = reuniao.ponte_receita(con)
    assert reuniao.total(r, "vendas", "receita") == pytest.approx(p.vendas)
    assert reuniao.total(r, "financeiro", "receita") == pytest.approx(p.financeiro)


def test_ponte_de_lojistas(con):
    p = reuniao.ponte_lojistas(con)
    assert (p.contratos, p.nunca_venderam, p.venderam) == (4, 2, 2)


def test_ponte_de_lojistas_fecha_em_cada_mes(con):
    for mes in ["2018-01", "2018-02", "2018-03", "2018-04"]:
        assert reuniao.ponte_lojistas_mes(con, mes).fecha(), mes


def test_ponte_de_lojistas_mensal_bate_com_as_consultas(con):
    r = reuniao.respostas(con)
    for mes in ["2018-01", "2018-02", "2018-03"]:
        p = reuniao.ponte_lojistas_mes(con, mes)
        assert p.marketing == (reuniao.total(r, "marketing", "lojistas conquistados", mes) or 0)
        assert p.vendas == (reuniao.total(r, "vendas", "lojistas conquistados", mes) or 0)
        assert p.operacao == (reuniao.total(r, "operacao", "lojistas conquistados", mes) or 0)


def test_ponte_de_clientes(con):
    p = reuniao.ponte_clientes(con)
    assert (p.customer_ids, p.pessoas, p.contados_a_mais) == (30, 26, 4)


def test_pagina_gerada(db_amostra_staging, tmp_path):
    saida = reuniao.gerar(db_amostra_staging, tmp_path / "a_reuniao.md", "2018-03")
    texto = saida.read_text(encoding="utf-8")
    assert "## A pauta: mar/2018" in texto
    assert "| lojistas conquistados |" in texto
    assert "None" not in texto
    assert "R$ nan" not in texto
