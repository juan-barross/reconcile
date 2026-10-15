"""A camada semântica tem que dar exatamente o número da camada única (marts)."""

import duckdb
import pytest

from ingest import pontes, semantica


@pytest.mark.parametrize("mes", ["2018-01", "2018-02", "2018-03"])
def test_metricflow_bate_com_os_marts(db_amostra_staging, mes):
    via_mf = semantica.por_mes(db_amostra_staging, mes)
    with duckdb.connect(str(db_amostra_staging), read_only=True) as con:
        via_marts = pontes.camada_unica(con, mes)

    for metrica, valor in via_marts.items():
        assert via_mf[metrica] == pytest.approx(valor, abs=0.01), (mes, metrica)


def test_leads_por_canal_soma_o_total(db_amostra_staging):
    linhas = semantica.consultar(
        db_amostra_staging, ("leads",), group_by=("metric_time__month", "lead__canal")
    )
    assert sum(float(x["leads"]) for x in linhas) == 10
    assert {x["lead__canal"] for x in linhas} >= {"unknown", "organic_search"}
