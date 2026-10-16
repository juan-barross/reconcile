from datetime import date
from pathlib import Path

from reconcile import base

CHECAGENS = base.dados("auditoria")
ULTIMA_CARGA = (
    "select tabela, linhas from raw._cargas qualify row_number() over "
    "(partition by tabela order by carregado_em desc) = 1 order by tabela"
)


def rodar(db_path: Path) -> list[tuple[dict, int]]:
    with base.ler(db_path) as con:
        return [(c, con.execute(c["sql"]).fetchone()[0]) for c in CHECAGENS]


def auditar(db_path: Path, saida: Path) -> Path:
    with base.ler(db_path) as con:
        cargas = con.execute(ULTIMA_CARGA).fetchall()
    checagens = [
        [c["categoria"], c["nome"], base.numero(v), c["leitura"]] for c, v in rodar(db_path)
    ]
    return base.escrever(
        saida,
        "auditoria",
        data=date.today().isoformat(),
        tabelas=base.tabela(["tabela", "linhas"], [[f"`{t}`", base.numero(q)] for t, q in cargas]),
        checagens=base.tabela(["categoria", "checagem", "resultado", "leitura"], checagens, "llrl"),
    )
