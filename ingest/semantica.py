"""Consulta a camada semântica (MetricFlow) pelo nome das métricas.

É a única porta para as métricas fora do dbt: o painel confere seus totais
contra ela e o agente da semana 6 só enxerga o que passa por aqui.
"""

import calendar
import csv
import os
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DBT_DIR = RAIZ / "dbt"

METRICAS = (
    "leads",
    "lojistas_contratados",
    "lojistas_ativados",
    "pedidos_validos",
    "clientes_novos",
    "receita_bruta",
    "receita_paga",
    "ticket_medio",
)


def consultar(
    db_path: Path,
    metricas: tuple[str, ...] = METRICAS,
    mes: str | None = None,
    group_by: tuple[str, ...] = ("metric_time__month",),
) -> list[dict[str, str]]:
    """Roda `mf query` e devolve as linhas do CSV. Valores vêm como texto."""
    args = ["query", "--metrics", ",".join(metricas), "--group-by", ",".join(group_by)]
    if mes:
        ano, m = (int(x) for x in mes.split("-"))
        ultimo = calendar.monthrange(ano, m)[1]
        args += ["--start-time", f"{mes}-01", "--end-time", f"{mes}-{ultimo:02d}"]

    with tempfile.TemporaryDirectory() as tmp:
        saida = Path(tmp) / "mf.csv"
        env = {
            **os.environ,
            "RECONCILE_DB_PATH": str(Path(db_path).resolve()),
            "DBT_PROFILES_DIR": str(DBT_DIR),
        }
        cmd = [sys.executable, "-c", "from dbt_metricflow.cli.main import cli; cli()"]
        r = subprocess.run(
            [*cmd, *args, "--csv", str(saida)],
            cwd=DBT_DIR,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if r.returncode != 0 or not saida.exists():
            raise RuntimeError(f"mf query falhou:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
        with saida.open(encoding="utf-8") as f:
            return list(csv.DictReader(f))


def por_mes(db_path: Path, mes: str, metricas: tuple[str, ...] = METRICAS) -> dict[str, float]:
    """Valor de cada métrica num mês. Métrica sem movimento no mês vale zero."""
    linhas = consultar(db_path, metricas, mes)
    valores = {m: 0.0 for m in metricas}
    for linha in linhas:
        if linha["metric_time__month"].startswith(mes):
            for m in metricas:
                if linha.get(m) not in (None, ""):
                    valores[m] = float(linha[m])
    return valores
