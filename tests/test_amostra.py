from reconcile import amostra
from reconcile.caminhos import FONTES


def test_amostra_e_deterministica():
    assert amostra.gerar() == amostra.gerar()


def test_cada_linha_tem_o_numero_de_colunas_do_cabecalho():
    for tabela, linhas in amostra.gerar().items():
        largura = len(amostra.CABECALHOS[tabela])
        assert all(len(linha) == largura for linha in linhas), tabela


def test_tamanhos_e_recompra():
    t = amostra.gerar()
    assert (len(t["orders"]), len(t["customers"]), len(t["closed_deals"])) == (30, 30, 4)
    assert len({linha[1] for linha in t["customers"]}) == 26


def test_escreve_um_csv_por_fonte(tmp_path):
    arquivos = amostra.escrever(tmp_path)
    assert sorted(a.name for a in arquivos) == sorted(f.arquivo for f in FONTES)
