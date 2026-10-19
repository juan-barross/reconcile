from pathlib import Path

from reconcile import base, pontes
from reconcile.base import numero as n
from reconcile.base import reais


def checagens(db_path: Path, mes: str) -> list[tuple[str, str, bool]]:
    with base.ler(db_path) as con:
        loj = pontes.ponte_lojistas_mes(con, mes)
        rec = pontes.ponte_receita(con, mes)
        oficial = pontes.camada_unica(con, mes)
    return [
        (
            "lojistas conquistados",
            f"marketing {n(loj['marketing'])}, vendas {n(loj['vendas'])}, "
            f"operação {n(loj['operacao'])}",
            pontes.fecha_lojistas(loj),
        ),
        (
            "receita",
            f"vendas {reais(rec['vendas'])}, financeiro {reais(rec['financeiro'])}",
            pontes.fecha_receita(rec),
        ),
        (
            "lojistas contratados na camada única",
            n(oficial["lojistas_contratados"]),
            oficial["lojistas_contratados"] == loj["vendas"],
        ),
    ]


def escrever(resultado: list[tuple[str, str, bool]], saida: Path, mes: str) -> Path:
    corpo = [[nome, valores, "sim" if ok else "**não**"] for nome, valores, ok in resultado]
    return base.escrever(
        saida,
        "veredito",
        mes=base.mes_extenso(mes),
        tabela=base.tabela(["checagem", "números", "a ponte fecha?"], corpo, "lll"),
    )
