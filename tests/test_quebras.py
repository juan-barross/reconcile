"""Cada cenário é um dbt build inteiro numa cópia, então só dois rodam aqui."""

from ingest.quebras import CENARIOS, rodar

POR_NOME = {c.nome: c for c in CENARIOS}


def test_controle_nao_falha(db_amostra):
    assert rodar(POR_NOME["controle"], db_amostra) == []


def test_chave_de_cliente_trocada_e_pega(db_amostra):
    falhas = rodar(POR_NOME["cliente contado por customer_id"], db_amostra)
    assert "clientes_contados_por_pessoa" in {f.teste for f in falhas}


def test_todo_cenario_tem_nome_unico_e_descricao():
    assert len(POR_NOME) == len(CENARIOS)
    assert all(c.o_que_mudou for c in CENARIOS)
