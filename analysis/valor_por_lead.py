"""Quanto vale um lead de cada canal, com intervalo e encolhimento.

Valor de um lead = P(lead vira contrato) x receita bruta média de um contrato
nos 180 dias seguintes. A base só permite 180 dias: o primeiro contrato é de
dez/2017 e a observação termina em ago/2018 (fim_observacao). Por isso a
receita por contrato usa só contratos com os 180 dias observados por inteiro.

Com 842 contratos espalhados em 10 canais, há canal com meia dúzia de
contratos. As duas partes da conta são encolhidas para a média geral na
proporção da incerteza de cada canal (empírico-bayesiano), e o intervalo vem
de bootstrap refazendo o encolhimento em cada reamostra.
"""

from dataclasses import dataclass

import duckdb
import numpy as np

JANELA = 180
B = 2000
SEMENTE = 42


@dataclass(frozen=True)
class Canal:
    canal: str
    leads: int
    contratos: int
    receitas_180d: np.ndarray  # uma por contrato com 180 dias observados


@dataclass(frozen=True)
class Estimativa:
    canal: str
    leads: int
    contratos: int
    contratos_observados: int
    conversao_bruta: float
    conversao: float  # encolhida
    receita_media_bruta: float
    receita_media: float  # encolhida
    valor: float  # GMV em 180 dias por lead
    valor_ic: tuple[float, float]
    conversao_ic: tuple[float, float]


def carregar(con: duckdb.DuckDBPyConnection) -> list[Canal]:
    leads = dict(con.execute("select canal, count(*) from marts.dim_leads group by 1").fetchall())
    contratos = dict(
        con.execute("select canal, count(*) from marts.fct_jornada_lojista group by 1").fetchall()
    )
    receitas: dict[str, list[float]] = {}
    for canal, receita in con.execute(
        "select canal, receita_bruta_180d from marts.fct_jornada_lojista where observado_180d"
    ).fetchall():
        receitas.setdefault(canal, []).append(float(receita))
    return [
        Canal(c, int(leads[c]), int(contratos.get(c, 0)), np.array(receitas.get(c, [])))
        for c in sorted(leads)
    ]


def encolher_proporcoes(x: np.ndarray, n: np.ndarray) -> np.ndarray:
    """Beta-binomial por momentos: força do prior m estimada da variação entre canais."""
    p0 = x.sum() / n.sum()
    p = x / n
    var_entre = np.var(p, ddof=1) - np.mean(p0 * (1 - p0) / n)
    if var_entre <= 0:
        return np.full_like(p, p0)
    m = max(p0 * (1 - p0) / var_entre - 1, 0.0)
    return (x + m * p0) / (n + m)


def encolher_medias(amostras: list[np.ndarray]) -> np.ndarray:
    """Normal-normal: cada média puxada para a média geral pelo peso tau²/(tau²+s²/n)."""
    todas = np.concatenate([a for a in amostras if len(a)])
    mu0 = todas.mean()
    s2 = todas.var(ddof=1)
    tem = [a for a in amostras if len(a)]
    medias = np.array([a.mean() for a in tem])
    ns = np.array([len(a) for a in tem])
    tau2 = max(np.var(medias, ddof=1) - np.mean(s2 / ns), 0.0) if len(tem) > 1 else 0.0
    saida = []
    for a in amostras:
        if not len(a):
            saida.append(mu0)
            continue
        w = tau2 / (tau2 + s2 / len(a)) if tau2 > 0 else 0.0
        saida.append(w * a.mean() + (1 - w) * mu0)
    return np.array(saida)


def _valores(canais: list[Canal], x: np.ndarray, amostras: list[np.ndarray]) -> np.ndarray:
    n = np.array([c.leads for c in canais], dtype=float)
    return encolher_proporcoes(x, n) * encolher_medias(amostras)


def estimar(canais: list[Canal], b: int = B, semente: int = SEMENTE) -> list[Estimativa]:
    rng = np.random.default_rng(semente)
    n = np.array([c.leads for c in canais], dtype=float)
    x = np.array([c.contratos for c in canais], dtype=float)
    amostras = [c.receitas_180d for c in canais]

    conv = encolher_proporcoes(x, n)
    media = encolher_medias(amostras)
    valor = conv * media

    reamostras = np.empty((b, len(canais)))
    conversoes = np.empty((b, len(canais)))
    for i in range(b):
        x_b = rng.binomial(n.astype(int), x / n).astype(float)
        a_b = [rng.choice(a, size=len(a), replace=True) if len(a) else a for a in amostras]
        conversoes[i] = encolher_proporcoes(x_b, n)
        reamostras[i] = conversoes[i] * encolher_medias(a_b)
    lo, hi = np.percentile(reamostras, [2.5, 97.5], axis=0)
    c_lo, c_hi = np.percentile(conversoes, [2.5, 97.5], axis=0)

    return [
        Estimativa(
            canal=c.canal,
            leads=c.leads,
            contratos=c.contratos,
            contratos_observados=len(c.receitas_180d),
            conversao_bruta=c.contratos / c.leads,
            conversao=float(conv[i]),
            receita_media_bruta=float(c.receitas_180d.mean()) if len(c.receitas_180d) else 0.0,
            receita_media=float(media[i]),
            valor=float(valor[i]),
            valor_ic=(float(lo[i]), float(hi[i])),
            conversao_ic=(float(c_lo[i]), float(c_hi[i])),
        )
        for i, c in enumerate(canais)
    ]


# --- Ativação: tempo do contrato até a primeira venda (Kaplan-Meier) ---------


@dataclass(frozen=True)
class Ativacao:
    canal: str
    contratos: int
    nunca_venderam: int
    ativado_ate: dict[int, float]  # dias -> fração ativada (1 - sobrevivência)


def kaplan_meier(tempos: np.ndarray, eventos: np.ndarray, pontos: tuple[int, ...]) -> dict:
    """Fração ativada até cada ponto, com censura à direita."""
    curva = curva_km(tempos, eventos)
    return {p: 1 - [s for tt, s in curva if tt <= p][-1] for p in pontos}


def curva_km(tempos: np.ndarray, eventos: np.ndarray) -> list[tuple[float, float]]:
    """Pontos (dia, fração ainda sem venda) da curva de Kaplan-Meier."""
    ordem = np.argsort(tempos, kind="stable")
    t, e = tempos[ordem], eventos[ordem]
    sobrevive, em_risco, i = 1.0, len(t), 0
    curva: list[tuple[float, float]] = [(0.0, 1.0)]
    while i < len(t):
        j = i
        while j < len(t) and t[j] == t[i]:
            j += 1
        d = e[i:j].sum()
        if d:
            sobrevive *= 1 - d / em_risco
            curva.append((float(t[i]), sobrevive))
        em_risco -= j - i
        i = j
    return curva


def tempos_de_ativacao(con: duckdb.DuckDBPyConnection) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """canal -> (tempos, eventos), com 'todos' somando os canais."""
    grupos: dict[str, list[tuple[bool, int]]] = {}
    for canal, evento, tempo in _linhas_ativacao(con):
        grupos.setdefault(canal, []).append((evento, tempo))
        grupos.setdefault("todos", []).append((evento, tempo))
    return {
        c: (np.array([t for _, t in obs], dtype=float), np.array([e for e, _ in obs], dtype=bool))
        for c, obs in grupos.items()
    }


def _linhas_ativacao(con: duckdb.DuckDBPyConnection) -> list[tuple[str, bool, int]]:
    # Primeira venda depois de fim_observacao conta como censura, não como evento:
    # a janela observada do contrato acabou antes.
    return con.execute(
        """
        with j as (
            select
                canal,
                coalesce(foi_ativado and dias_contrato_ate_primeira_venda <= dias_observados,
                         false) as evento,
                dias_contrato_ate_primeira_venda,
                dias_observados
            from marts.fct_jornada_lojista
        )
        select canal, evento,
               case when evento then dias_contrato_ate_primeira_venda else dias_observados end
        from j
        """
    ).fetchall()


def ativacao(con: duckdb.DuckDBPyConnection, pontos=(30, 90, 180)) -> list[Ativacao]:
    """Fração ativada em 30, 90 e 180 dias, por canal, com censura."""
    saida = []
    for canal, (tempos, eventos) in sorted(
        tempos_de_ativacao(con).items(), key=lambda kv: -len(kv[1][0])
    ):
        saida.append(
            Ativacao(
                canal, len(tempos), int((~eventos).sum()), kaplan_meier(tempos, eventos, pontos)
            )
        )
    return saida
