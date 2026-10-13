"""Comando `reconcile`: ponto de entrada único do projeto.

reconcile tudo              # dado real da Olist (baixa do Kaggle, ~45 MB)
reconcile --amostra tudo    # amostra sintética, sem rede, em segundos
"""

import os
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

from ingest.fontes import Caminhos, caminhos

app = typer.Typer(
    help="Reconcile: por que as áreas da Olist têm números diferentes.", no_args_is_help=True
)
console = Console()

DBT_DIR = Path(__file__).resolve().parent.parent / "dbt"


def _n(x: int) -> str:
    return f"{x:,}".replace(",", ".")


@app.callback()
def main(
    ctx: typer.Context,
    amostra: bool = typer.Option(
        False, "--amostra", help="Usa a amostra sintética em data/amostra em vez do dado real."
    ),
) -> None:
    """Reconcile: por que as áreas da Olist têm números diferentes."""
    ctx.obj = caminhos(amostra)


@app.command()
def baixar(ctx: typer.Context) -> None:
    """Baixa os CSVs da Olist do Kaggle (ou gera a amostra sintética)."""
    c: Caminhos = ctx.obj
    if c.amostra:
        from ingest.amostra import escrever

        arquivos = escrever(c.csv_dir)
    else:
        from ingest.baixar import baixar as _baixar

        arquivos = _baixar(c.csv_dir)
    console.print(f"[green]{len(arquivos)} CSVs em {c.csv_dir}[/]")


@app.command()
def carregar(ctx: typer.Context) -> None:
    """Carrega os CSVs no esquema raw do DuckDB, como texto."""
    from rich.table import Table

    from ingest.carregar import carregar as _carregar

    c: Caminhos = ctx.obj
    tabela = Table("tabela raw", "linhas", title=f"Carga em {c.db_path}")
    for carga in _carregar(c.csv_dir, c.db_path):
        tabela.add_row(carga.tabela, _n(carga.linhas))
    console.print(tabela)


@app.command()
def auditar(ctx: typer.Context) -> None:
    """Roda as checagens da camada raw e grava o relatório em markdown."""
    from ingest.auditoria import auditar as _auditar

    c: Caminhos = ctx.obj
    # O relatório do dado real é versionado em docs/; o da amostra fica em data/.
    saida = c.base / "auditoria.md" if c.amostra else Path("docs/auditoria.md")
    console.print(f"[green]Auditoria em {_auditar(c.db_path, saida)}[/]")


def rodar_dbt(db_path: Path, *args: str) -> bool:
    """Roda o dbt num subprocesso apontando para db_path.

    Subprocesso, e não dbtRunner, porque o dbt-duckdb deixa a conexão com o
    arquivo aberta no processo, e a leitura seguinte (read_only) falharia.
    """
    env = {**os.environ, "RECONCILE_DB_PATH": str(db_path.resolve())}
    comum = ["--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR)]
    dbt_cli = [sys.executable, "-c", "from dbt.cli.main import cli; cli()"]
    if not (DBT_DIR / "dbt_packages").exists():
        subprocess.run([*dbt_cli, "deps", *comum], env=env, check=True)
    return subprocess.run([*dbt_cli, *args, *comum], env=env).returncode == 0


def _dbt(c: Caminhos, *args: str) -> None:
    if not rodar_dbt(c.db_path, *args):
        console.print(f"[red]dbt {' '.join(args)} falhou[/]")
        raise typer.Exit(1)


@app.command()
def dbt(ctx: typer.Context) -> None:
    """Roda `dbt build`: modelos e testes de staging, intermediate e marts."""
    _dbt(ctx.obj, "build")


MES_PADRAO = "2018-03"


@app.command()
def reuniao(
    ctx: typer.Context,
    mes: str = typer.Option(MES_PADRAO, help="Mês da pauta, no formato AAAA-MM."),
) -> None:
    """Roda a consulta de cada área e gera a página da reunião, com as pontes."""
    from ingest.reuniao import gerar

    c: Caminhos = ctx.obj
    saida = c.base / "a_reuniao.md" if c.amostra else Path("docs/a_reuniao.md")
    console.print(f"[green]Reunião em {gerar(c.db_path, saida, mes)}[/]")


@app.command()
def metricas(
    ctx: typer.Context,
    mes: str = typer.Option(MES_PADRAO, help="Mês, no formato AAAA-MM."),
) -> None:
    """Consulta as métricas do contrato na camada semântica (MetricFlow)."""
    from rich.table import Table

    from ingest.semantica import por_mes

    c: Caminhos = ctx.obj
    tabela = Table("métrica", mes, title="Camada semântica (mf query)")
    for metrica, valor in por_mes(c.db_path, mes).items():
        texto = f"{valor:,.2f}" if metrica.startswith(("receita", "ticket")) else f"{valor:,.0f}"
        tabela.add_row(metrica, texto.replace(",", "X").replace(".", ",").replace("X", "."))
    console.print(tabela)


@app.command()
def tudo(ctx: typer.Context) -> None:
    """Baixa, carrega, audita, roda o dbt e gera a reunião, nessa ordem."""
    for passo in (baixar, carregar, auditar, dbt):
        console.rule(passo.__name__)
        passo(ctx)
    console.rule("reuniao")
    reuniao(ctx, mes=MES_PADRAO)
