import shutil

import pytest

from reconcile import amostra, projeto_dbt
from reconcile.carregar import carregar


@pytest.fixture(scope="session")
def db_amostra(tmp_path_factory):
    pasta = tmp_path_factory.mktemp("amostra")
    amostra.escrever(pasta / "csv")
    db = pasta / "olist.duckdb"
    carregar(pasta / "csv", db)
    return db


@pytest.fixture(scope="session")
def db_amostra_staging(db_amostra, tmp_path_factory):
    db = tmp_path_factory.mktemp("dbt") / "olist.duckdb"
    shutil.copyfile(db_amostra, db)
    assert projeto_dbt.dbt(db, "run", "--quiet").returncode == 0
    return db
