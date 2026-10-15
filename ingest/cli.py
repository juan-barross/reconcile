"""CLI do projeto.

reconcile tudo              # dado real da Olist, baixado do Kaggle
reconcile --amostra tudo    # amostra sintética, sem rede
"""

import typer
from rich.console import Console
from rich.table import Table

from ingest.fontes import Caminhos, caminhos
from ingest.formato import numero

app = typer.Typer(help="Por que as áreas da Olist têm números diferentes.", no_args_is_help=True)
console = Console()

MES_PADRAO = "2018-03"
OPCAO_MES = typer.Option(MES_PADRAO, help="Mês no formato AAAA-MM.")


@app.callback()
def main(
    ctx: typer.Context,
    amostra: bool = typer.Option(False, "--amostra", help="Usa a amostra sintética."),
) -> None:
    ctx.obj = caminhos(amostra)


@app.command()
def baixar(ctx: typer.Context) -> None:
    """Baixa os CSVs da Olist (ou gera a amostra sintética)."""
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
    """Carrega os CSVs no esquema raw do DuckDB."""
    from ingest.carregar import carregar as _carregar

    c: Caminhos = ctx.obj
    tabela = Table("tabela raw", "linhas", title=f"Carga em {c.db_path}")
    for carga in _carregar(c.csv_dir, c.db_path):
        tabela.add_row(carga.tabela, numero(carga.linhas))
    console.print(tabela)


@app.command()
def auditar(ctx: typer.Context) -> None:
    """Checa chaves, órfãos e datas da camada raw."""
    from ingest.auditoria import auditar as _auditar

    c: Caminhos = ctx.obj
    console.print(f"[green]Auditoria em {_auditar(c.db_path, c.relatorio('auditoria.md'))}[/]")


@app.command()
def dbt(ctx: typer.Context) -> None:
    """Roda dbt build: modelos e testes."""
    from ingest import projeto_dbt

    if projeto_dbt.dbt(ctx.obj.db_path, "build").returncode != 0:
        console.print("[red]dbt build falhou[/]")
        raise typer.Exit(1)


@app.command()
def reuniao(ctx: typer.Context, mes: str = OPCAO_MES) -> None:
    """Gera a reunião: a resposta de cada área e as pontes entre elas."""
    from ingest.reuniao import gerar

    c: Caminhos = ctx.obj
    console.print(f"[green]Reunião em {gerar(c.db_path, c.relatorio('a_reuniao.md'), mes)}[/]")


@app.command()
def metricas(ctx: typer.Context, mes: str = OPCAO_MES) -> None:
    """Consulta as métricas do contrato no MetricFlow."""
    from ingest.semantica import por_mes

    tabela = Table("métrica", mes, title="mf query")
    for metrica, valor in por_mes(ctx.obj.db_path, mes).items():
        casas = 2 if metrica.startswith(("receita", "ticket")) else 0
        tabela.add_row(metrica, numero(valor, casas))
    console.print(tabela)


@app.command()
def quebrar(ctx: typer.Context) -> None:
    """Reintroduz cada divergência numa cópia e mostra o teste que a pega."""
    from ingest.quebras import gerar

    c: Caminhos = ctx.obj
    base = "a amostra sintética" if c.amostra else "o dado real da Olist"
    saida, resultados = gerar(c.db_path, c.relatorio("o_dia_que_mexeram_na_origem.md"), base)
    for cenario, falhas in resultados:
        esperado = cenario.nome == "controle"
        cor = "green" if esperado == (not falhas) else "red"
        console.print(f"[{cor}]{cenario.nome}: {len(falhas)} teste(s) falharam[/]")
    console.print(f"[green]Relatório em {saida}[/]")


@app.command()
def crescimento(ctx: typer.Context) -> None:
    """Valor por lead, ativação e Growth Review."""
    from analysis.growth_review import gerar

    c: Caminhos = ctx.obj
    console.print(f"[green]Growth Review em {gerar(c.db_path, c.docs_dir)}[/]")


@app.command()
def tudo(ctx: typer.Context) -> None:
    """Baixa, carrega, audita, roda o dbt e gera reunião e Growth Review."""
    for passo in (baixar, carregar, auditar, dbt):
        console.rule(passo.__name__)
        passo(ctx)
    console.rule("reuniao")
    reuniao(ctx, mes=MES_PADRAO)
    console.rule("crescimento")
    crescimento(ctx)
