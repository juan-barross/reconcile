from typer.testing import CliRunner

from reconcile import caminhos, crescimento, veredito
from reconcile.cli import app

rodar = CliRunner().invoke


def test_ajuda_lista_os_comandos():
    saida = rodar(app, ["--help"]).output
    for comando in ("tudo", "reuniao", "painel", "quebrar", "avaliar"):
        assert comando in saida


def test_amostra_baixa_carrega_e_audita(tmp_path, monkeypatch):
    monkeypatch.setattr(caminhos, "DATA_DIR", tmp_path)
    for comando in ("baixar", "carregar", "auditar"):
        assert rodar(app, ["--amostra", comando]).exit_code == 0, comando
    assert (tmp_path / "amostra" / "olist.duckdb").exists()
    assert "Checagens" in (tmp_path / "amostra" / "auditoria.md").read_text(encoding="utf-8")


def test_veredito_fecha_as_pontes_na_amostra(db_amostra_staging, tmp_path):
    resultado = veredito.checagens(db_amostra_staging, "2018-01")
    assert all(ok for *_, ok in resultado)
    texto = veredito.escrever(resultado, tmp_path / "v.md", "2018-01").read_text(encoding="utf-8")
    assert "jan/2018" in texto and "**não**" not in texto


def test_veredito_acusa_ponte_que_nao_fecha(tmp_path):
    texto = veredito.escrever([("receita", "1, 2", False)], tmp_path / "v.md", "2018-03")
    assert "| receita | 1, 2 | **não** |" in texto.read_text(encoding="utf-8")


def test_growth_review_na_amostra(db_amostra_staging, tmp_path):
    texto = crescimento.gerar(db_amostra_staging, tmp_path).read_text(encoding="utf-8")
    assert "## Recomendações" in texto
    assert (tmp_path / "img" / "conversao_por_canal.png").exists()
