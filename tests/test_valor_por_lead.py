import numpy as np
import pytest

from analysis.valor_por_lead import (
    Canal,
    encolher_medias,
    encolher_proporcoes,
    estimar,
    kaplan_meier,
)


def test_kaplan_meier_confere_com_a_conta_a_mao():
    # 5 contratos: vendas nos dias 10 e 20, censurados nos dias 15, 30 e 40.
    # Em 10: 1 de 5 vende -> S = 0,8. Em 20: 1 de 3 em risco -> S = 0,8 * 2/3.
    tempos = np.array([10, 15, 20, 30, 40], dtype=float)
    eventos = np.array([True, False, True, False, False])
    ativado = kaplan_meier(tempos, eventos, (5, 10, 25))
    assert ativado[5] == pytest.approx(0.0)
    assert ativado[10] == pytest.approx(0.2)
    assert ativado[25] == pytest.approx(1 - 0.8 * 2 / 3)


def test_encolhimento_nao_mexe_quando_os_canais_sao_iguais():
    x = np.array([10.0, 20.0, 40.0])
    n = np.array([100.0, 200.0, 400.0])
    assert encolher_proporcoes(x, n) == pytest.approx([0.1, 0.1, 0.1])


def test_encolhimento_puxa_mais_o_canal_pequeno():
    x = np.array([300.0, 280.0, 2.0])
    n = np.array([1000.0, 2000.0, 5.0])  # o terceiro tem 40% com só 5 leads
    p = encolher_proporcoes(x, n)
    bruto = x / n
    assert abs(p[2] - bruto[2]) > abs(p[0] - bruto[0])
    assert p[2] < bruto[2]


def test_media_encolhida_fica_entre_a_bruta_e_a_geral():
    rng = np.random.default_rng(0)
    amostras = [rng.exponential(100, size=k) for k in (3, 5, 8, 40, 60, 300)]
    medias = encolher_medias(amostras)
    geral = np.concatenate(amostras).mean()
    for a, m in zip(amostras, medias, strict=True):
        assert min(a.mean(), geral) - 1e-9 <= m <= max(a.mean(), geral) + 1e-9
    # quem tem menos dados anda proporcionalmente mais em direção à média geral
    andou = [
        abs(a.mean() - m) / abs(a.mean() - geral) for a, m in zip(amostras, medias, strict=True)
    ]
    assert andou[0] >= andou[-1]


def test_estimar_e_reprodutivel_e_o_intervalo_contem_a_estimativa():
    rng = np.random.default_rng(1)
    canais = [
        Canal("a", 500, 80, rng.exponential(1500, size=30)),
        Canal("b", 400, 20, rng.exponential(1500, size=8)),
        Canal("c", 50, 2, np.array([])),
    ]
    um, dois = estimar(canais, b=300), estimar(canais, b=300)
    assert [e.valor_ic for e in um] == [e.valor_ic for e in dois]
    for e in um:
        assert e.valor_ic[0] <= e.valor <= e.valor_ic[1]
        assert e.conversao_ic[0] <= e.conversao <= e.conversao_ic[1]
