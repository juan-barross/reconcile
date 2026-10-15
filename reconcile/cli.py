import typer
from rich.console import Console
from rich.table import Table

from reconcile.caminhos import Caminhos, caminhos
from reconcile.formato import numero

app = typer.Typer(help="Por que as áreas da Olist têm números diferentes.", no_args_is_help=True)
console = Console()

MES_PADRAO = "2018-03"
OPCAO_MES = typer.Option(MES_PADRAO, help="Mês no formato AAAA-MM.")


def _feito(o_que: str, onde) -> None:
    console.print(f"[green]{o_que} em {onde}[/]")


@app.callback()
def main(
    ctx: typer.Context,
    amostra: bool = typer.Option(False, "--amostra", help="Usa a amostra sintética."),
) -> None:
    ctx.obj = caminhos(amostra)


@app.command(help="Baixa os CSVs da Olist (ou gera a amostra sintética).")
def baixar(ctx: typer.Context) -> None:
    c: Caminhos = ctx.obj
    if c.amostra:
        from reconcile.amostra import escrever as obter
    else:
        from reconcile.baixar import baixar as obter
    _feito(f"{len(obter(c.csv_dir))} CSVs", c.csv_dir)


@app.command(help="Carrega os CSVs no esquema raw do DuckDB.")
def carregar(ctx: typer.Context) -> None:
    from reconcile.carregar import carregar as _carregar

    c: Caminhos = ctx.obj
    tabela = Table("tabela raw", "linhas", title=f"Carga em {c.db_path}")
    for carga in _carregar(c.csv_dir, c.db_path):
        tabela.add_row(carga.tabela, numero(carga.linhas))
    console.print(tabela)


@app.command(help="Checa chaves, órfãos e datas da camada raw.")
def auditar(ctx: typer.Context) -> None:
    from reconcile.auditoria import auditar as _auditar

    c: Caminhos = ctx.obj
    _feito("Auditoria", _auditar(c.db_path, c.docs_dir / "auditoria.md"))


@app.command(help="Roda dbt build: modelos e testes.")
def dbt(ctx: typer.Context) -> None:
    from reconcile import projeto_dbt

    if projeto_dbt.dbt(ctx.obj.db_path, "build").returncode != 0:
        console.print("[red]dbt build falhou[/]")
        raise typer.Exit(1)


@app.command(help="Gera a reunião: a resposta de cada área e as pontes entre elas.")
def reuniao(ctx: typer.Context, mes: str = OPCAO_MES) -> None:
    from reconcile.reuniao import gerar

    c: Caminhos = ctx.obj
    _feito("Reunião", gerar(c.db_path, c.docs_dir / "a_reuniao.md", mes))


@app.command(help="Gera o painel com as métricas do contrato, mês a mês.")
def painel(ctx: typer.Context) -> None:
    from reconcile.painel import gerar

    c: Caminhos = ctx.obj
    _feito("Painel", gerar(c.db_path, c.docs_dir))


@app.command(help="Consulta as métricas do contrato no MetricFlow.")
def metricas(ctx: typer.Context, mes: str = OPCAO_MES) -> None:
    from reconcile.semantica import por_mes

    tabela = Table("métrica", mes, title="mf query")
    for metrica, valor in por_mes(ctx.obj.db_path, mes).items():
        tabela.add_row(
            metrica, numero(valor, 2 if metrica.startswith(("receita", "ticket")) else 0)
        )
    console.print(tabela)


@app.command(help="Reintroduz cada divergência numa cópia e mostra o teste que a pega.")
def quebrar(ctx: typer.Context) -> None:
    from reconcile.quebras import gerar

    c: Caminhos = ctx.obj
    base = "a amostra sintética" if c.amostra else "o dado real da Olist"
    saida, resultados = gerar(c.db_path, c.docs_dir / "o_dia_que_mexeram_na_origem.md", base)
    for cenario, falhas in resultados:
        cor = "green" if (cenario.nome == "controle") == (not falhas) else "red"
        console.print(f"[{cor}]{cenario.nome}: {len(falhas)} teste(s) falharam[/]")
    _feito("Relatório", saida)


@app.command(help="Valor por lead, ativação e Growth Review.")
def crescimento(ctx: typer.Context) -> None:
    from reconcile.crescimento import gerar

    c: Caminhos = ctx.obj
    _feito("Growth Review", gerar(c.db_path, c.docs_dir))


@app.command(help="Faz uma pergunta ao agente (versão A: SQL no raw; B: métricas do contrato).")
def perguntar(ctx: typer.Context, pergunta: str, versao: str = "B") -> None:
    from reconcile.agente import perguntar as _perguntar

    console.print(_perguntar(pergunta, versao.upper(), ctx.obj.db_path).texto)


@app.command(help="Avalia as versões A e B do agente contra o painel (usa a API da Anthropic).")
def avaliar(
    ctx: typer.Context,
    gerar_perguntas: bool = typer.Option(False, help="Só regenera avaliacao/perguntas.jsonl."),
) -> None:
    from reconcile import avaliacao

    c: Caminhos = ctx.obj
    if gerar_perguntas:
        _feito("Perguntas", avaliacao.gerar_perguntas(c.db_path))
    else:
        _feito("Avaliação", avaliacao.gerar_relatorio(c.db_path, c.docs_dir / "agente.md"))


@app.command(help="Baixa, carrega, audita, roda o dbt e gera reunião, painel e Growth Review.")
def tudo(ctx: typer.Context) -> None:
    for passo in (baixar, carregar, auditar, dbt, painel, crescimento):
        console.rule(passo.__name__)
        passo(ctx)
    console.rule("reuniao")
    reuniao(ctx, mes=MES_PADRAO)
