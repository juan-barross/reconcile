"""O dia em que alguém mexeu na origem: quebra o dado de propósito e mostra qual
teste pega cada quebra.

Cada cenário roda numa cópia do banco e do projeto dbt, em pasta temporária.
Um cenário pode mudar o dado bruto (SQL em raw) ou o código de um modelo
(troca de trecho num .sql), que são os dois jeitos reais de a divergência voltar.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
DBT_DIR = RAIZ / "dbt"


@dataclass(frozen=True)
class Cenario:
    nome: str
    o_que_mudou: str
    sql_raw: tuple[str, ...] = ()
    # (arquivo relativo a dbt/, trecho original, trecho novo)
    trocas: tuple[tuple[str, str, str], ...] = field(default_factory=tuple)


CENARIOS: tuple[Cenario, ...] = (
    Cenario(
        "controle",
        "Nada. Serve para mostrar que, sem mudança, nenhum teste falha.",
    ),
    Cenario(
        "pagamento duplicado na origem",
        "O sistema de pagamentos reenviou cerca de 5% dos pagamentos (mesmo pedido, "
        "mesma sequência).",
        sql_raw=(
            "insert into raw.order_payments select * from raw.order_payments "
            "where hash(order_id) % 20 = 0",
        ),
    ),
    Cenario(
        "cliente duplicado na origem",
        "O cadastro exportou de novo cerca de 2% dos clientes.",
        sql_raw=(
            "insert into raw.customers select * from raw.customers "
            "where hash(customer_id) % 50 = 0",
        ),
    ),
    Cenario(
        "cliente contado por customer_id",
        "Alguém trocou a chave de cliente para customer_id no intermediate.",
        trocas=(
            (
                "models/intermediate/int_pedidos__valores.sql",
                "    c.customer_unique_id,\n",
                "    o.customer_id as customer_unique_id,\n",
            ),
        ),
    ),
    Cenario(
        "cancelados de volta",
        "Alguém tirou o filtro de status da regra de pedido válido.",
        trocas=(
            (
                "models/intermediate/int_pedidos__valores.sql",
                "        o.order_status not in ('canceled', 'unavailable')\n        and ",
                "        ",
            ),
        ),
    ),
    Cenario(
        "regra de data trocada",
        "Alguém passou a datar a receita paga pela compra, e não pela aprovação.",
        trocas=(
            (
                "models/intermediate/int_pedidos__valores.sql",
                "coalesce(o.approved_at, o.purchased_at) as receita_paga_em",
                "o.purchased_at as receita_paga_em",
            ),
        ),
    ),
)


@dataclass(frozen=True)
class Falha:
    teste: str
    linhas: int


def _copiar_dbt(destino: Path) -> Path:
    alvo = destino / "dbt"
    shutil.copytree(DBT_DIR, alvo, ignore=shutil.ignore_patterns("target", "logs", ".user.yml"))
    return alvo


def rodar(cenario: Cenario, db_origem: Path) -> list[Falha]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        db = tmp / "olist.duckdb"
        shutil.copyfile(db_origem, db)
        projeto = _copiar_dbt(tmp)

        if cenario.sql_raw:
            with duckdb.connect(str(db)) as con:
                for sql in cenario.sql_raw:
                    con.execute(sql)

        for arquivo, antes, depois in cenario.trocas:
            caminho = projeto / arquivo
            texto = caminho.read_text(encoding="utf-8")
            if antes not in texto:
                raise ValueError(f"{cenario.nome}: trecho não encontrado em {arquivo}")
            caminho.write_text(texto.replace(antes, depois), encoding="utf-8", newline="\n")

        env = {**os.environ, "RECONCILE_DB_PATH": str(db)}
        cmd = [sys.executable, "-c", "from dbt.cli.main import cli; cli()"]
        alvo = tmp / "target"
        subprocess.run(
            [*cmd, "build", "--project-dir", str(projeto), "--profiles-dir", str(projeto),
             "--target-path", str(alvo), "--quiet"],
            env=env, capture_output=True,
        )  # fmt: skip
        resultados = json.loads((alvo / "run_results.json").read_text(encoding="utf-8"))

    falhas = []
    for r in resultados["results"]:
        if r["status"] in ("fail", "error"):
            nome = r["unique_id"].split(".")[2]
            falhas.append(Falha(nome, int(r.get("failures") or 0)))
    return sorted(falhas, key=lambda f: f.teste)


def _linhas(n: int) -> str:
    if not n:
        return ""
    return f" ({n:,} {'linha' if n == 1 else 'linhas'})".replace(",", ".")


def para_markdown(resultados: list[tuple[Cenario, list[Falha]]], base: str) -> str:
    partes = [
        "# O dia em que alguém mexeu na origem",
        "",
        f"Gerado por `reconcile quebrar` em {date.today().isoformat()} sobre {base}. "
        "Não edite à mão.",
        "",
        "Cada cenário abaixo reintroduz, de propósito e numa cópia, uma das causas de "
        "divergência da [reunião](a_reuniao.md): pelo dado bruto ou pelo código de um "
        "modelo. O `dbt build` roda inteiro e a tabela diz quais testes pegaram a quebra. "
        "Um cenário sem nenhum teste falhando seria uma divergência que voltaria calada.",
        "",
        "Quando um teste do staging falha, o `dbt build` não constrói os modelos que "
        "dependem dele. Por isso a quebra na origem aparece num teste só: os marts, e o "
        "painel que lê os marts, nunca chegam a ver o dado duplicado.",
        "",
        "| cenário | o que mudou | testes que falharam |",
        "|---|---|---|",
    ]
    for c, falhas in resultados:
        if falhas:
            lista = "<br>".join(f"`{f.teste}`" + _linhas(f.linhas) for f in falhas)
        else:
            lista = "nenhum"
        partes.append(f"| **{c.nome}** | {c.o_que_mudou} | {lista} |")
    partes.append("")
    return "\n".join(partes)


def gerar(db_origem: Path, saida: Path, base: str) -> tuple[Path, list[tuple[Cenario, list]]]:
    resultados = [(c, rodar(c, db_origem)) for c in CENARIOS]
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(para_markdown(resultados, base), encoding="utf-8", newline="\n")
    return saida, resultados
