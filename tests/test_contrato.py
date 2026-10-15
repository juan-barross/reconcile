"""docs/contrato_de_metricas.md, os marts e a camada semântica listam as mesmas métricas."""

import re

import yaml

from ingest.fontes import RAIZ
from ingest.semantica import METRICAS

CONTRATO = RAIZ / "docs" / "contrato_de_metricas.md"
MARTS_YML = RAIZ / "dbt" / "models" / "marts" / "_marts.yml"
TESTES_SQL = RAIZ / "dbt" / "tests"


def metricas_do_contrato() -> set[str]:
    texto = CONTRATO.read_text(encoding="utf-8")
    resumo = texto.split("## Resumo", 1)[1].split("\n## ", 1)[0]
    return set(re.findall(r"^\| `(\w+)` \|", resumo, flags=re.MULTILINE))


def marts() -> list[dict]:
    return yaml.safe_load(MARTS_YML.read_text(encoding="utf-8"))["models"]


def tem_teste(mart: dict) -> bool:
    if mart.get("data_tests"):
        return True
    if any(c.get("data_tests") for c in mart.get("columns", [])):
        return True
    ref = f"ref('{mart['name']}')"
    return any(ref in p.read_text(encoding="utf-8") for p in TESTES_SQL.glob("*.sql"))


def test_contrato_e_camada_semantica_tem_as_mesmas_metricas():
    assert metricas_do_contrato() == set(METRICAS)


def test_toda_metrica_tem_um_mart_testado():
    declaradas: dict[str, list[str]] = {}
    for m in marts():
        for metrica in m.get("config", {}).get("meta", {}).get("metricas", []):
            declaradas.setdefault(metrica, []).append(m["name"])
        assert tem_teste(m), f"{m['name']} não tem nenhum teste"

    sem_mart = metricas_do_contrato() - set(declaradas)
    assert not sem_mart, f"métricas do contrato sem mart: {sorted(sem_mart)}"


def test_mart_nao_inventa_metrica():
    contrato = metricas_do_contrato()
    for m in marts():
        extras = set(m.get("config", {}).get("meta", {}).get("metricas", [])) - contrato
        assert not extras, f"{m['name']} declara métricas fora do contrato: {sorted(extras)}"


def test_todo_mart_tem_contrato_de_modelo():
    for m in marts():
        assert m.get("config", {}).get("contract", {}).get("enforced") is True, m["name"]
        for coluna in m["columns"]:
            assert "data_type" in coluna, f"{m['name']}.{coluna['name']} sem data_type"
