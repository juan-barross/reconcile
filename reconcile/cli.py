import typer
from rich.console import Console
from rich.table import Table

from reconcile import (
    agente,
    amostra,
    auditoria,
    avaliacao,
    crescimento,
    painel,
    projeto_dbt,
    quebras,
    reuniao,
    semantica,
    veredito,
)
from reconcile import baixar as kaggle
from reconcile import carregar as carga
from reconcile.base import numero
from reconcile.caminhos import Caminhos, caminhos

app = typer.Typer(help="Por que as áreas da Olist têm números diferentes.", no_args_is_help=True)
console = Console()
MES = "2018-03"
OPCAO_MES = typer.Option(MES, help="Mês no formato AAAA-MM.")


def _feito(o_que: str, onde) -> None:
    console.print(f"[green]{o_que} em {onde}[/]")


@app.callback()
def main(ctx: typer.Context, amostra: bool = typer.Option(False, help="Usa a amostra.")) -> None:
    ctx.obj = caminhos(amostra)


@app.command("baixar", help="Baixa os CSVs da Olist (ou gera a amostra sintética).")
def cmd_baixar(ctx: typer.Context) -> None:
    c: Caminhos = ctx.obj
    obter = amostra.escrever if c.amostra else kaggle.baixar
    _feito(f"{len(obter(c.csv_dir))} CSVs", c.csv_dir)


@app.command("carregar", help="Carrega os CSVs no esquema raw do DuckDB.")
def cmd_carregar(ctx: typer.Context) -> None:
    c: Caminhos = ctx.obj
    tabela = Table("tabela raw", "linhas", title=f"Carga em {c.db_path}")
    for item in carga.carregar(c.csv_dir, c.db_path):
        tabela.add_row(item.tabela, numero(item.linhas))
    console.print(tabela)


@app.command("auditar", help="Checa chaves, órfãos e datas da camada raw.")
def cmd_auditar(ctx: typer.Context) -> None:
    _feito("Auditoria", auditoria.auditar(ctx.obj.db_path, ctx.obj.docs_dir / "auditoria.md"))


@app.command("dbt", help="Roda dbt build: modelos e testes.")
def cmd_dbt(ctx: typer.Context) -> None:
    ok = projeto_dbt.dbt(ctx.obj.db_path, "build", "--quiet").returncode == 0
    resultados = projeto_dbt.resultados()
    passaram = sum(r["status"] in ("success", "pass") for r in resultados)
    cor = "green" if ok else "red"
    console.print(f"[{cor}]dbt build: {passaram} de {len(resultados)} passaram[/]")
    if not ok:
        raise typer.Exit(1)


@app.command("reuniao", help="A resposta de cada área e as pontes entre elas.")
def cmd_reuniao(ctx: typer.Context, mes: str = OPCAO_MES) -> None:
    c: Caminhos = ctx.obj
    _feito("Reunião", reuniao.gerar(c.db_path, c.docs_dir / "a_reuniao.md", mes))


@app.command("painel", help="As métricas do contrato, mês a mês.")
def cmd_painel(ctx: typer.Context) -> None:
    _feito("Painel", painel.gerar(ctx.obj.db_path, ctx.obj.docs_dir))


@app.command("metricas", help="As métricas do contrato pelo MetricFlow.")
def cmd_metricas(ctx: typer.Context, mes: str = OPCAO_MES) -> None:
    tabela = Table("métrica", mes, title="mf query")
    for metrica, valor in semantica.por_mes(ctx.obj.db_path, mes).items():
        casas = 2 if metrica.startswith(("receita", "ticket")) else 0
        tabela.add_row(metrica, numero(valor, casas))
    console.print(tabela)


@app.command("quebrar", help="Reintroduz cada divergência numa cópia e mostra o teste que a pega.")
def cmd_quebrar(ctx: typer.Context) -> None:
    c: Caminhos = ctx.obj
    origem = "a amostra sintética" if c.amostra else "o dado real da Olist"
    saida, resultados = quebras.gerar(
        c.db_path, c.docs_dir / "o_dia_que_mexeram_na_origem.md", origem
    )
    for cenario, falhas in resultados:
        cor = "green" if (cenario["nome"] == "controle") == (not falhas) else "red"
        console.print(f"[{cor}]{cenario['nome']}: {len(falhas)} teste(s) falharam[/]")
    _feito("Relatório", saida)


@app.command("crescimento", help="Valor por lead, ativação e Growth Review.")
def cmd_crescimento(ctx: typer.Context) -> None:
    _feito("Growth Review", crescimento.gerar(ctx.obj.db_path, ctx.obj.docs_dir))


@app.command("perguntar", help="Pergunta ao agente (A: SQL no raw; B: métricas do contrato).")
def cmd_perguntar(ctx: typer.Context, pergunta: str, versao: str = "B") -> None:
    console.print(agente.perguntar(pergunta, versao.upper(), ctx.obj.db_path).texto)


@app.command("avaliar", help="Avalia as versões A e B do agente contra o painel (pede chave).")
def cmd_avaliar(ctx: typer.Context, gerar_perguntas: bool = False) -> None:
    c: Caminhos = ctx.obj
    if gerar_perguntas:
        _feito("Perguntas", avaliacao.gerar_perguntas(c.db_path))
    else:
        _feito("Avaliação", avaliacao.gerar_relatorio(c.db_path, c.docs_dir / "agente.md"))


@app.command("veredito", help="Confere se as pontes entre as áreas fecham.")
def cmd_veredito(ctx: typer.Context, mes: str = OPCAO_MES) -> None:
    c: Caminhos = ctx.obj
    resultado = veredito.checagens(c.db_path, mes)
    tabela = Table("checagem", "números", "fecha?", title=f"Veredito de {mes}")
    for nome, valores, ok in resultado:
        tabela.add_row(nome, valores, "[green]sim[/]" if ok else "[red]não[/]")
    console.print(tabela)
    _feito("Veredito", veredito.escrever(resultado, c.docs_dir / "veredito.md", mes))
    if not all(ok for *_, ok in resultado):
        raise typer.Exit(1)


@app.command("tudo", help="Baixa, carrega, audita, roda o dbt e gera os relatórios.")
def cmd_tudo(ctx: typer.Context) -> None:
    passos = [cmd_baixar, cmd_carregar, cmd_auditar, cmd_dbt, cmd_painel, cmd_crescimento]
    for passo in passos:
        console.rule(passo.__name__.removeprefix("cmd_"))
        passo(ctx)
    for passo in (cmd_reuniao, cmd_veredito):
        console.rule(passo.__name__.removeprefix("cmd_"))
        passo(ctx, mes=MES)
