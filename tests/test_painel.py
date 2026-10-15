from reconcile import painel


def test_painel_tem_graficos_e_uma_linha_por_mes(db_amostra_staging, tmp_path):
    texto = painel.gerar(db_amostra_staging, tmp_path).read_text(encoding="utf-8")
    assert (tmp_path / "img" / "painel_lojistas.png").exists()
    assert (tmp_path / "img" / "painel_receita.png").exists()
    assert sum(linha.startswith("| ") and "/2018 |" in linha for linha in texto.splitlines()) == 8
