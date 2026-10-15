"""Chamadas ao dbt e ao MetricFlow.

Rodam em subprocesso porque o dbt-duckdb mantém o arquivo do banco aberto no
processo que o chama, e a leitura seguinte em modo read_only falharia.
"""

import os
import subprocess
import sys
from pathlib import Path

from ingest.fontes import RAIZ

DBT_DIR = RAIZ / "dbt"

_DBT = [sys.executable, "-c", "from dbt.cli.main import cli; cli()"]
_MF = [sys.executable, "-c", "from dbt_metricflow.cli.main import cli; cli()"]


def _ambiente(db_path: Path) -> dict[str, str]:
    return {
        **os.environ,
        "RECONCILE_DB_PATH": str(Path(db_path).resolve()),
        "DBT_PROFILES_DIR": str(DBT_DIR),
    }


def _projeto(caminho: Path) -> list[str]:
    return ["--project-dir", str(caminho), "--profiles-dir", str(caminho)]


def instalar_pacotes() -> None:
    if not (DBT_DIR / "dbt_packages").exists():
        subprocess.run([*_DBT, "deps", *_projeto(DBT_DIR)], check=True)


def dbt(
    db_path: Path, *args: str, projeto: Path = DBT_DIR, silencioso: bool = False
) -> subprocess.CompletedProcess:
    instalar_pacotes()
    return subprocess.run(
        [*_DBT, *args, *_projeto(projeto)],
        env=_ambiente(db_path),
        capture_output=silencioso,
    )


def mf(db_path: Path, *args: str) -> subprocess.CompletedProcess:
    instalar_pacotes()
    return subprocess.run(
        [*_MF, *args],
        cwd=DBT_DIR,
        env=_ambiente(db_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
