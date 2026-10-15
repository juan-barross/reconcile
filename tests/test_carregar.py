import duckdb
import pytest

from reconcile.caminhos import FONTES
from reconcile.carregar import carregar


@pytest.fixture
def csv_dir(tmp_path):
    pasta = tmp_path / "csv"
    pasta.mkdir()
    for fonte in FONTES:
        (pasta / fonte.arquivo).write_text("id,cep\na,01037\nb,99999\n", encoding="utf-8")
    return pasta


def test_carrega_todas_as_tabelas_como_texto(csv_dir, tmp_path):
    db = tmp_path / "t.duckdb"
    cargas = carregar(csv_dir, db)

    assert [c.tabela for c in cargas] == [f.tabela for f in FONTES]
    assert all(c.linhas == 2 for c in cargas)

    with duckdb.connect(str(db)) as con:
        tipos = con.execute(
            "select distinct data_type from information_schema.columns "
            "where table_schema = 'raw' and table_name = 'customers'"
        ).fetchall()
        cep = con.execute("select cep from raw.customers where id = 'a'").fetchone()[0]
    assert tipos == [("VARCHAR",)]

    assert cep == "01037"


def test_registra_cada_carga(csv_dir, tmp_path):
    db = tmp_path / "t.duckdb"
    carregar(csv_dir, db)
    carregar(csv_dir, db)

    with duckdb.connect(str(db)) as con:
        n, hashes = con.execute(
            "select count(*), count(distinct sha256) from raw._cargas"
        ).fetchone()
    assert n == 2 * len(FONTES)
    assert hashes == 1


def test_falha_com_mensagem_clara_sem_o_csv(csv_dir, tmp_path):
    (csv_dir / FONTES[0].arquivo).unlink()
    with pytest.raises(FileNotFoundError, match="reconcile baixar"):
        carregar(csv_dir, tmp_path / "t.duckdb")
