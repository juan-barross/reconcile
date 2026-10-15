import calendar
import csv
import tempfile
from pathlib import Path

from reconcile import projeto_dbt

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
    args = ["query", "--metrics", ",".join(metricas), "--group-by", ",".join(group_by)]
    if mes:
        ano, m = map(int, mes.split("-"))
        ultimo_dia = calendar.monthrange(ano, m)[1]
        args += ["--start-time", f"{mes}-01", "--end-time", f"{mes}-{ultimo_dia:02d}"]

    with tempfile.TemporaryDirectory() as tmp:
        saida = Path(tmp) / "mf.csv"
        r = projeto_dbt.mf(db_path, *args, "--csv", str(saida))
        if r.returncode != 0 or not saida.exists():
            raise RuntimeError(f"mf query falhou:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
        with saida.open(encoding="utf-8") as f:
            return list(csv.DictReader(f))


def por_mes(db_path: Path, mes: str, metricas: tuple[str, ...] = METRICAS) -> dict[str, float]:
    valores = dict.fromkeys(metricas, 0.0)
    for linha in consultar(db_path, metricas, mes):
        if linha["metric_time__month"].startswith(mes):
            valores.update({m: float(linha[m]) for m in metricas if linha.get(m)})
    return valores
