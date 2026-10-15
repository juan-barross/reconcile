"""Valor de um lead por canal e tempo até a primeira venda.

Valor = P(lead vira contrato) x receita bruta média do contrato nos 180 dias
seguintes. As duas partes são encolhidas para a média geral (empírico-bayesiano),
porque há canal com meia dúzia de contratos, e o intervalo vem de bootstrap.
"""

from dataclasses import dataclass

import duckdb
import numpy as np

JANELA = 180  # o contrato mais antigo tem ~270 dias observados; 12 meses não cabem
B = 2000
SEMENTE = 42


@dataclass(frozen=True)
class Canal:
    canal: str
    leads: int
    contratos: int
    receitas_180d: np.ndarray  # contratos com a janela inteira observada


@dataclass(frozen=True)
class Estimativa:
    canal: str
    leads: int
    contratos: int
    contratos_observados: int
    conversao_bruta: float
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
    nunca_venderam: int
    ativado_ate: dict[int, float]


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
    """Beta-binomial pelo método dos momentos."""
    p0 = x.sum() / n.sum()
    var_entre = np.var(x / n, ddof=1) - np.mean(p0 * (1 - p0) / n)
    if var_entre <= 0:
        return np.full(len(x), p0)
    forca_prior = max(p0 * (1 - p0) / var_entre - 1, 0.0)
    return (x + forca_prior * p0) / (n + forca_prior)


def encolher_medias(amostras: list[np.ndarray]) -> np.ndarray:
    """Normal-normal: peso tau² / (tau² + s²/n) para a média do canal."""
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

    conversao = encolher_proporcoes(x, n)
    media = encolher_medias(amostras)

    conversoes = np.empty((b, len(canais)))
    valores = np.empty((b, len(canais)))
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
            conversao_bruta=c.contratos / c.leads,
            conversao=float(conversao[i]),
            receita_media_bruta=float(c.receitas_180d.mean()) if len(c.receitas_180d) else 0.0,
            receita_media=float(media[i]),
            valor=float(conversao[i] * media[i]),
            valor_ic=(float(valor_ic[0, i]), float(valor_ic[1, i])),
            conversao_ic=(float(conversao_ic[0, i]), float(conversao_ic[1, i])),
        )
        for i, c in enumerate(canais)
    ]


def curva_km(tempos: np.ndarray, eventos: np.ndarray) -> list[tuple[float, float]]:
    """Kaplan-Meier: (dia, fração ainda sem venda), com censura à direita."""
    dias, indice = np.unique(tempos, return_inverse=True)
    vendas = np.bincount(indice, weights=eventos.astype(float))
    saidas = np.bincount(indice)
    em_risco = len(tempos) - np.concatenate(([0], np.cumsum(saidas)[:-1]))
    sobrevivencia = np.cumprod(1 - vendas / em_risco)
    return [(0.0, 1.0), *zip(dias.tolist(), sobrevivencia.tolist(), strict=True)]


def kaplan_meier(tempos: np.ndarray, eventos: np.ndarray, pontos: tuple[int, ...]) -> dict:
    """Fração ativada até cada ponto."""
    dias, sobrevivencia = map(np.array, zip(*curva_km(tempos, eventos), strict=True))
    posicao = np.searchsorted(dias, pontos, side="right") - 1
    return {p: float(1 - sobrevivencia[i]) for p, i in zip(pontos, posicao, strict=True)}


def tempos_de_ativacao(con: duckdb.DuckDBPyConnection) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """canal -> (dias, vendeu?), com 'todos' somando os canais."""
    # Venda depois de fim_observacao é censura: a janela observada acabou antes.
    linhas = con.execute(
        """
        with j as (
            select
                canal,
                coalesce(
                    foi_ativado and dias_contrato_ate_primeira_venda <= dias_observados, false
                ) as vendeu,
                dias_contrato_ate_primeira_venda,
                dias_observados
            from marts.fct_jornada_lojista
        )

        select
            canal,
            vendeu,
            case when vendeu then dias_contrato_ate_primeira_venda else dias_observados end
        from j
        """
    ).fetchall()
    grupos: dict[str, list[tuple[bool, int]]] = {}
    for canal, vendeu, dias in linhas:
        grupos.setdefault(canal, []).append((vendeu, dias))
        grupos.setdefault("todos", []).append((vendeu, dias))
    return {
        canal: (np.array([d for _, d in obs], dtype=float), np.array([v for v, _ in obs]))
        for canal, obs in grupos.items()
    }


def ativacao(con: duckdb.DuckDBPyConnection, pontos=(30, 90, JANELA)) -> list[Ativacao]:
    """Fração ativada em cada ponto, por canal, do maior para o menor."""
    grupos = sorted(tempos_de_ativacao(con).items(), key=lambda kv: -len(kv[1][0]))
    return [
        Ativacao(canal, len(dias), int((~vendeu).sum()), kaplan_meier(dias, vendeu, pontos))
        for canal, (dias, vendeu) in grupos
    ]
