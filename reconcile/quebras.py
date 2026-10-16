import json
import shutil
import tempfile
from datetime import date
from pathlib import Path

import duckdb

from reconcile import base, projeto_dbt

CENARIOS = base.dados("quebras")


def _preparar(cenario: dict, db: Path, projeto: Path) -> None:
    with duckdb.connect(str(db)) as con:
        for comando in cenario.get("sql_raw", []):
            con.execute(comando)
    for troca in cenario.get("trocas", []):
        arquivo = projeto / troca["arquivo"]
        texto = arquivo.read_text(encoding="utf-8")
        if troca["antes"] not in texto:
            raise ValueError(f"{cenario['nome']}: trecho não encontrado em {troca['arquivo']}")
        arquivo.write_text(texto.replace(troca["antes"], troca["depois"]), encoding="utf-8")


def rodar(cenario: dict, db_origem: Path) -> list[tuple[str, int]]:
    projeto_dbt.instalar_pacotes()
    with tempfile.TemporaryDirectory() as pasta:
        pasta = Path(pasta)
        db, projeto, alvo = pasta / "olist.duckdb", pasta / "dbt", pasta / "target"
        shutil.copyfile(db_origem, db)
        shutil.copytree(
            projeto_dbt.DBT_DIR, projeto, ignore=shutil.ignore_patterns("target", "logs")
        )
        _preparar(cenario, db, projeto)
        args = ["build", "--target-path", str(alvo), "--quiet"]
        projeto_dbt.dbt(db, *args, projeto=projeto, silencioso=True)
        resultados = json.loads((alvo / "run_results.json").read_text(encoding="utf-8"))["results"]
    falhas = [r for r in resultados if r["status"] in ("fail", "error")]
    return sorted((r["unique_id"].split(".")[2], int(r.get("failures") or 0)) for r in falhas)


def _falhas(falhas: list[tuple[str, int]]) -> str:
    def linhas(q: int) -> str:
        return f" ({base.numero(q)} {'linha' if q == 1 else 'linhas'})" if q else ""

    return "<br>".join(f"`{teste}`{linhas(q)}" for teste, q in falhas) or "nenhum"


def gerar(db_origem: Path, saida: Path, descricao: str) -> tuple[Path, list]:
    resultados = [(c, rodar(c, db_origem)) for c in CENARIOS]
    corpo = [[f"**{c['nome']}**", c["o_que_mudou"], _falhas(f)] for c, f in resultados]
    tabela = base.tabela(["cenário", "o que mudou", "testes que falharam"], corpo, "lll")
    hoje = date.today().isoformat()
    return base.escrever(saida, "quebras", data=hoje, base=descricao, tabela=tabela), resultados
