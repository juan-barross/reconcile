from collections import defaultdict
from dataclasses import dataclass

import duckdb
import numpy as np

from reconcile import base

JANELA = 180
B = 2000
SEMENTE = 42


@dataclass(frozen=True)
class Canal:
    canal: str
    leads: int
    contratos: int
    receitas_180d: np.ndarray


@dataclass(frozen=True)
class Estimativa:
    canal: str
    leads: int
    contratos: int
    contratos_observados: int
    conversao: float
    receita_media_bruta: float
    receita_media: float
    valor: float
    valor_ic: tuple[float, float]
    conversao_ic: tuple[float, float]


@dataclass(frozen=True)
class Ativacao:
    canal: str
    contratos: int
    ativado_ate: dict[int, float]


def carregar(con: duckdb.DuckDBPyConnection) -> list[Canal]:
    receitas = defaultdict(list)
    for canal, receita in base.linhas(con, "receitas_180d"):
        receitas[canal].append(receita)
    return [
        Canal(canal, leads, contratos, np.array(receitas[canal]))
        for canal, leads, contratos in base.linhas(con, "leads_por_canal")
    ]


def encolher_proporcoes(x: np.ndarray, n: np.ndarray) -> np.ndarray:
    p0 = x.sum() / n.sum()
    var_entre = np.var(x / n, ddof=1) - np.mean(p0 * (1 - p0) / n)
    if var_entre <= 0:
        return np.full(len(x), p0)
    forca_prior = max(p0 * (1 - p0) / var_entre - 1, 0.0)
    return (x + forca_prior * p0) / (n + forca_prior)


def encolher_medias(amostras: list[np.ndarray]) -> np.ndarray:
    com_dados = [a for a in amostras if len(a)]
    todas = np.concatenate(com_dados)
    mu0, s2 = todas.mean(), todas.var(ddof=1)
    medias = np.array([a.mean() for a in com_dados])
    ns = np.array([len(a) for a in com_dados])
    tau2 = max(np.var(medias, ddof=1) - np.mean(s2 / ns), 0.0) if len(com_dados) > 1 else 0.0

    def encolhida(a: np.ndarray) -> float:
        if not len(a) or tau2 == 0:
            return mu0
        peso = tau2 / (tau2 + s2 / len(a))
        return peso * a.mean() + (1 - peso) * mu0

    return np.array([encolhida(a) for a in amostras])


def estimar(canais: list[Canal], b: int = B, semente: int = SEMENTE) -> list[Estimativa]:
    rng = np.random.default_rng(semente)
    n = np.array([c.leads for c in canais], dtype=float)
    x = np.array([c.contratos for c in canais], dtype=float)
    amostras = [c.receitas_180d for c in canais]
    conversao, media = encolher_proporcoes(x, n), encolher_medias(amostras)

    conversoes, valores = np.empty((b, len(canais))), np.empty((b, len(canais)))
    for i in range(b):
        conversoes[i] = encolher_proporcoes(rng.binomial(n.astype(int), x / n).astype(float), n)
        reamostra = [rng.choice(a, size=len(a)) if len(a) else a for a in amostras]
        valores[i] = conversoes[i] * encolher_medias(reamostra)
    valor_ic = np.percentile(valores, [2.5, 97.5], axis=0)
    conversao_ic = np.percentile(conversoes, [2.5, 97.5], axis=0)

    return [
        Estimativa(
            canal=c.canal,
            leads=c.leads,
            contratos=c.contratos,
            contratos_observados=len(c.receitas_180d),
            conversao=float(conversao[i]),
            receita_media_bruta=float(c.receitas_180d.mean()) if len(c.receitas_180d) else 0.0,
            receita_media=float(media[i]),
            valor=float(conversao[i] * media[i]),
            valor_ic=tuple(map(float, valor_ic[:, i])),
            conversao_ic=tuple(map(float, conversao_ic[:, i])),
        )
        for i, c in enumerate(canais)
    ]


def curva_km(tempos: np.ndarray, eventos: np.ndarray) -> list[tuple[float, float]]:
    dias, indice = np.unique(tempos, return_inverse=True)
    vendas = np.bincount(indice, weights=eventos.astype(float))
    em_risco = len(tempos) - np.concatenate(([0], np.cumsum(np.bincount(indice))[:-1]))
    sobrevivencia = np.cumprod(1 - vendas / em_risco)
    return [(0.0, 1.0), *zip(dias.tolist(), sobrevivencia.tolist(), strict=True)]


def kaplan_meier(tempos: np.ndarray, eventos: np.ndarray, pontos: tuple[int, ...]) -> dict:
    dias, sobrevivencia = map(np.array, zip(*curva_km(tempos, eventos), strict=True))
    posicao = np.searchsorted(dias, pontos, side="right") - 1
    return {p: float(1 - sobrevivencia[i]) for p, i in zip(pontos, posicao, strict=True)}


def tempos_de_ativacao(con: duckdb.DuckDBPyConnection) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    grupos = defaultdict(list)
    for canal, vendeu, dias in base.linhas(con, "ativacao"):
        for grupo in (canal, "todos"):
            grupos[grupo].append((dias, vendeu))
    return {g: tuple(map(np.array, zip(*obs, strict=True))) for g, obs in grupos.items()}


def ativacao(con: duckdb.DuckDBPyConnection, pontos=(30, 90, JANELA)) -> list[Ativacao]:
    grupos = sorted(tempos_de_ativacao(con).items(), key=lambda kv: -len(kv[1][0]))
    return [
        Ativacao(canal, len(dias), kaplan_meier(dias.astype(float), vendeu.astype(bool), pontos))
        for canal, (dias, vendeu) in grupos
    ]
