import pytest

from ingest import amostra
from ingest.carregar import carregar


@pytest.fixture(scope="session")
def db_amostra(tmp_path_factory):
    """DuckDB com a amostra sintética carregada em raw."""
    pasta = tmp_path_factory.mktemp("amostra")
    amostra.escrever(pasta / "csv")
    db = pasta / "olist.duckdb"
    carregar(pasta / "csv", db)
    return db


@pytest.fixture(scope="session")
def db_amostra_staging(db_amostra, tmp_path_factory):
    """A amostra com todas as camadas do dbt construídas (staging a marts)."""
    import shutil

    from ingest.cli import rodar_dbt

    db = tmp_path_factory.mktemp("staging") / "olist.duckdb"
    shutil.copyfile(db_amostra, db)
    assert rodar_dbt(db, "run", "--quiet")
    return db
