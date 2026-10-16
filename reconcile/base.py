from decimal import Decimal
from pathlib import Path

import duckdb
import yaml

PACOTE = Path(__file__).parent
TRACO = "—"
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def ler(db_path: Path) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(db_path), read_only=True)


def sql(nome: str) -> str:
    return (PACOTE / "sql" / f"{nome}.sql").read_text(encoding="utf-8")


def dados(nome: str):
    return yaml.safe_load((PACOTE / f"{nome}.yml").read_text(encoding="utf-8"))


def _python(valor):
    return float(valor) if isinstance(valor, Decimal) else valor


def linha(con: duckdb.DuckDBPyConnection, nome: str, **params) -> dict:
    cursor = con.execute(sql(nome), params)
    colunas = [c[0] for c in cursor.description]
    return {c: _python(v) for c, v in zip(colunas, cursor.fetchone(), strict=True)}


def linhas(con: duckdb.DuckDBPyConnection, nome: str, **params) -> list[tuple]:
    return [tuple(map(_python, t)) for t in con.execute(sql(nome), params).fetchall()]


def escrever(saida: Path, modelo: str, /, **valores) -> Path:
    texto = (PACOTE / "modelos" / f"{modelo}.md").read_text(encoding="utf-8")
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(texto.format(**valores), encoding="utf-8", newline="\n")
    return saida


def tabela(cabecalho: list[str], corpo: list[list], alinhar: str = "") -> str:
    alinhar = alinhar or "l" + "r" * (len(cabecalho) - 1)
    regua = "|" + "|".join("---:" if a == "r" else "---" for a in alinhar) + "|"
    linhas = ["| " + " | ".join(map(str, c)) + " |" for c in [cabecalho, *corpo]]
    return "\n".join([linhas[0].replace("|  |", "| |"), regua, *linhas[1:]])


def numero(valor: float | None, casas: int = 0) -> str:
    if valor is None:
        return TRACO
    return f"{valor:,.{casas}f}".translate(str.maketrans(",.", ".,"))


def reais(valor: float | None, casas: int = 2, sinal: bool = False) -> str:
    if valor is None:
        return TRACO
    texto = f"R$ {numero(abs(valor), casas)}"
    if sinal:
        return f"{'+' if valor >= 0 else '−'} {texto}"
    return f"−{texto}" if valor < 0 else texto


def milhoes(valor: float, casas: int = 1) -> str:
    return f"R$ {numero(valor / 1e6, casas)} mi"


def pct(fracao: float, casas: int = 1) -> str:
    return f"{numero(100 * fracao, casas)}%"


def mes_extenso(mes: str) -> str:
    ano, m = mes.split("-")
    return f"{MESES[int(m) - 1]}/{ano}"
