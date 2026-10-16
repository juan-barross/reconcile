import csv
from pathlib import Path

import pytest

from reconcile import amostra
from reconcile.auditoria import CHECAGENS, auditar, rodar
from reconcile.caminhos import FONTES


def test_auditoria_acha_cada_anomalia_plantada(db_amostra):
    resultados = {c["nome"]: n for c, n in rodar(db_amostra)}
    for nome, esperado in amostra.PLANTADAS.items():
        assert resultados[nome] == esperado, nome


def test_toda_checagem_plantada_existe():
    nomes = {c["nome"] for c in CHECAGENS}
    assert set(amostra.PLANTADAS) <= nomes


def test_relatorio_tem_uma_linha_por_checagem(db_amostra, tmp_path):
    saida = auditar(db_amostra, tmp_path / "auditoria.md")
    texto = saida.read_text(encoding="utf-8")
    for c in CHECAGENS:
        assert f"| {c['nome']} |" in texto
    assert b"\r\n" not in saida.read_bytes()


CSV_REAL = Path("data/csv")


@pytest.mark.skipif(not CSV_REAL.exists(), reason="sem os CSVs reais (rode `reconcile baixar`)")
def test_amostra_tem_os_mesmos_cabecalhos_do_dado_real():
    for fonte in FONTES:
        with (CSV_REAL / fonte.arquivo).open(encoding="utf-8-sig") as f:
            real = next(csv.reader(f))
        assert amostra.CABECALHOS[fonte.tabela] == real, fonte.arquivo
