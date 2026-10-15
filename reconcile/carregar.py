import hashlib
from dataclasses import dataclass
from pathlib import Path

import duckdb

from reconcile.caminhos import FONTES, Fonte


@dataclass(frozen=True)
class Carga:
    tabela: str
    arquivo: str
    linhas: int
    sha256: str


def _sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        while bloco := f.read(1 << 20):
            h.update(bloco)
    return h.hexdigest()


def carregar_fonte(con: duckdb.DuckDBPyConnection, fonte: Fonte, csv_dir: Path) -> Carga:
    caminho = csv_dir / fonte.arquivo
    if not caminho.exists():
        raise FileNotFoundError(f"{caminho} não existe. Rode `reconcile baixar` antes.")

    con.execute(
        f"""
        create or replace table raw.{fonte.tabela} as
        select * from read_csv(
            ?, header = true, all_varchar = true, sample_size = -1, strict_mode = true
        )
        """,
        [str(caminho)],
    )
    (linhas,) = con.execute(f"select count(*) from raw.{fonte.tabela}").fetchone()
    return Carga(fonte.tabela, fonte.arquivo, linhas, _sha256(caminho))


def carregar(csv_dir: Path, db_path: Path) -> list[Carga]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(db_path)) as con:
        con.execute("create schema if not exists raw")
        con.execute(
            """
            create table if not exists raw._cargas (
                tabela varchar, arquivo varchar, linhas bigint, sha256 varchar,
                carregado_em timestamp default current_timestamp
            )
            """
        )
        cargas = [carregar_fonte(con, f, csv_dir) for f in FONTES]
        con.executemany(
            "insert into raw._cargas (tabela, arquivo, linhas, sha256) values (?, ?, ?, ?)",
            [(c.tabela, c.arquivo, c.linhas, c.sha256) for c in cargas],
        )
    return cargas
