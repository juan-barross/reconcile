"""Gráficos do Growth Review, na paleta de referência do guia de visualização."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from analysis.valor_por_lead import JANELA, Estimativa, curva_km  # noqa: E402
from ingest.formato import pct  # noqa: E402

SUPERFICIE = "#fcfcfb"
TEXTO = "#0b0b0b"
TEXTO_2 = "#52514e"
GRADE = "#e4e3df"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]


def _eixos(altura: float):
    fig, ax = plt.subplots(figsize=(7.2, altura), dpi=150, facecolor=SUPERFICIE)
    ax.set_facecolor(SUPERFICIE)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(GRADE)
    ax.tick_params(colors=TEXTO_2, labelsize=9, length=0)
    ax.set_axisbelow(True)
    return fig, ax


def _titulo(ax, titulo: str, subtitulo: str) -> None:
    ax.set_title(titulo, loc="left", fontsize=11, color=TEXTO, fontweight="bold", pad=20)
    ax.text(0, 1.015, subtitulo, transform=ax.transAxes, fontsize=8, color=TEXTO_2, va="bottom")


def _porcentagem(eixo) -> None:
    eixo.set_major_formatter(lambda v, _: f"{100 * v:.0f}%")


def _afastar(posicoes: list[float], minimo: float) -> list[float]:
    """Empurra rótulos para cima até ficarem a `minimo` um do outro."""
    ordem = sorted(range(len(posicoes)), key=posicoes.__getitem__)
    saida = list(posicoes)
    for anterior, atual in zip(ordem, ordem[1:], strict=False):
        saida[atual] = max(saida[atual], saida[anterior] + minimo)
    return saida


def conversao_por_canal(estimativas: list[Estimativa], geral: float, saida: Path) -> None:
    ordem = sorted(estimativas, key=lambda e: e.conversao)
    fig, ax = _eixos(altura=4.4)
    for y, e in enumerate(ordem):
        ax.plot(e.conversao_ic, [y, y], color=SERIES[0], lw=2, solid_capstyle="round", alpha=0.45)
        ax.plot(e.conversao, y, "o", ms=7, color=SERIES[0], mec=SUPERFICIE, mew=2)
        ax.text(
            e.conversao_ic[1] + 0.004, y, pct(e.conversao), va="center", fontsize=8.5, color=TEXTO
        )
    ax.axvline(geral, color=TEXTO_2, lw=1, ls=(0, (3, 3)))
    ax.text(geral + 0.002, -0.95, f"média geral {pct(geral)}", fontsize=8, color=TEXTO_2)
    ax.set_ylim(-1.3, len(ordem) - 0.5)
    ax.set_yticks(range(len(ordem)), [f"{e.canal} ({e.contratos})" for e in ordem], color=TEXTO)
    _porcentagem(ax.xaxis)
    ax.grid(axis="x", color=GRADE, lw=0.8)
    _titulo(
        ax,
        "Conversão de lead em contrato, por canal",
        "ponto: estimativa com encolhimento · traço: IC 95% (bootstrap) · "
        "entre parênteses: contratos",
    )
    fig.tight_layout()
    fig.savefig(saida, facecolor=SUPERFICIE)
    plt.close(fig)


def ativacao_por_canal(tempos: dict, canais: list[str], saida: Path) -> None:
    # Depois de JANELA dias sobram poucos contratos em risco e a curva só dá saltos.
    fig, ax = _eixos(altura=3.9)
    finais = []
    for cor, canal in zip(SERIES, canais, strict=False):
        pontos = [(d, 1 - s) for d, s in curva_km(*tempos[canal]) if d <= JANELA]
        xs = [d for d, _ in pontos] + [JANELA]
        ys = [f for _, f in pontos] + [pontos[-1][1]]
        ax.step(xs, ys, where="post", color=cor, lw=2)
        finais.append((canal, ys[-1]))
    for (canal, y), altura in zip(finais, _afastar([y for _, y in finais], 0.035), strict=True):
        ax.text(JANELA + 3, altura, f"{canal} {pct(y)}", va="center", fontsize=8.5, color=TEXTO)
    ax.axvline(90, color=GRADE, lw=1)
    ax.set_xlim(0, JANELA)
    ax.set_xticks(range(0, JANELA + 1, 30))
    ax.set_ylim(0, 0.75)
    _porcentagem(ax.yaxis)
    ax.set_xlabel("dias desde a assinatura do contrato", fontsize=9, color=TEXTO_2)
    ax.grid(axis="y", color=GRADE, lw=0.8)
    _titulo(
        ax,
        "Lojistas que já fizeram a primeira venda",
        "Kaplan-Meier, com censura em 31/08/2018 · três maiores canais",
    )
    fig.subplots_adjust(right=0.76)
    fig.savefig(saida, facecolor=SUPERFICIE, bbox_inches="tight")
    plt.close(fig)
