"""Reintroduz cada causa de divergência numa cópia do banco e do projeto dbt e
registra qual teste falha.

Um cenário altera o dado bruto (SQL em raw), o código de um modelo (troca de
trecho num .sql) ou nada, no caso do controle.
"""

import json
import shutil
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb

from ingest import projeto_dbt
from ingest.formato import numero

INT_PEDIDOS = "models/intermediate/int_pedidos__valores.sql"


@dataclass(frozen=True)
class Cenario:
    nome: str
    o_que_mudou: str
    sql_raw: tuple[str, ...] = ()
    trocas: tuple[tuple[str, str, str], ...] = ()  # (arquivo, trecho original, trecho novo)


@dataclass(frozen=True)
class Falha:
    teste: str
    linhas: int


CENARIOS: tuple[Cenario, ...] = (
    Cenario("controle", "Nada. Sem mudança, nenhum teste pode falhar."),
    Cenario(
        "pagamento duplicado na origem",
        "O sistema de pagamentos reenviou cerca de 5% dos pagamentos.",
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
        "A chave de cliente foi trocada para customer_id no intermediate.",
        trocas=(
            (INT_PEDIDOS, "c.customer_unique_id,\n", "o.customer_id as customer_unique_id,\n"),
        ),
    ),
    Cenario(
        "cancelados de volta",
        "O filtro de status saiu da regra de pedido válido.",
        trocas=(
            (INT_PEDIDOS, "o.order_status not in ('canceled', 'unavailable')\n        and ", ""),
        ),
    ),
    Cenario(
        "regra de data trocada",
        "A receita paga passou a ser datada pela compra, e não pela aprovação.",
        trocas=(
            (
                INT_PEDIDOS,
                "coalesce(o.approved_at, o.purchased_at) as receita_paga_em",
                "o.purchased_at as receita_paga_em",
            ),
        ),
    ),
)


def _aplicar_trocas(cenario: Cenario, projeto: Path) -> None:
    for arquivo, antes, depois in cenario.trocas:
        caminho = projeto / arquivo
        texto = caminho.read_text(encoding="utf-8")
        if antes not in texto:
            raise ValueError(f"{cenario.nome}: trecho não encontrado em {arquivo}")
        caminho.write_text(texto.replace(antes, depois), encoding="utf-8", newline="\n")


def _falhas(run_results: Path) -> list[Falha]:
    resultados = json.loads(run_results.read_text(encoding="utf-8"))["results"]
    falhas = [
        Falha(r["unique_id"].split(".")[2], int(r.get("failures") or 0))
        for r in resultados
        if r["status"] in ("fail", "error")
    ]
    return sorted(falhas, key=lambda f: f.teste)


def rodar(cenario: Cenario, db_origem: Path) -> list[Falha]:
    projeto_dbt.instalar_pacotes()  # a cópia do projeto precisa levar os pacotes
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        db = tmp / "olist.duckdb"
        shutil.copyfile(db_origem, db)
        projeto = tmp / "dbt"
        shutil.copytree(
            projeto_dbt.DBT_DIR, projeto, ignore=shutil.ignore_patterns("target", "logs")
        )

        if cenario.sql_raw:
            with duckdb.connect(str(db)) as con:
                for sql in cenario.sql_raw:
                    con.execute(sql)
        _aplicar_trocas(cenario, projeto)

        alvo = tmp / "target"
        projeto_dbt.dbt(
            db, "build", "--target-path", str(alvo), "--quiet", projeto=projeto, silencioso=True
        )
        return _falhas(alvo / "run_results.json")


def _linhas(n: int) -> str:
    if not n:
        return ""
    return f" ({numero(n)} {'linha' if n == 1 else 'linhas'})"


def para_markdown(resultados: list[tuple[Cenario, list[Falha]]], base: str) -> str:
    linhas = [
        "# O dia em que alguém mexeu na origem",
        "",
        f"Gerado por `reconcile quebrar` em {date.today().isoformat()} sobre {base}. "
        "Não edite à mão.",
        "",
        "Cada cenário reintroduz, numa cópia, uma das causas de divergência da "
        "[reunião](a_reuniao.md), pelo dado bruto ou pelo código de um modelo, e roda o "
        "`dbt build` inteiro. A tabela mostra os testes que falharam.",
        "",
        "Quando um teste do staging falha, o dbt não constrói os modelos que dependem dele. "
        "Por isso a quebra na origem aparece num teste só: os marts nunca recebem o dado "
        "duplicado.",
        "",
        "| cenário | o que mudou | testes que falharam |",
        "|---|---|---|",
    ]
    for cenario, falhas in resultados:
        lista = "<br>".join(f"`{f.teste}`{_linhas(f.linhas)}" for f in falhas) or "nenhum"
        linhas.append(f"| **{cenario.nome}** | {cenario.o_que_mudou} | {lista} |")
    linhas.append("")
    return "\n".join(linhas)


def gerar(db_origem: Path, saida: Path, base: str) -> tuple[Path, list[tuple[Cenario, list]]]:
    resultados = [(c, rodar(c, db_origem)) for c in CENARIOS]
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(para_markdown(resultados, base), encoding="utf-8", newline="\n")
    return saida, resultados
