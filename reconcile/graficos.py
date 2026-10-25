from pathlib import Path

from reconcile.base import pct
from reconcile.valor_por_lead import JANELA, Estimativa, curva_km

SUPERFICIE = "#fcfcfb"
TEXTO = "#0b0b0b"
TEXTO_2 = "#52514e"
GRADE = "#e4e3df"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]


def eixos(altura: float):
    from matplotlib.figure import Figure

    fig = Figure(figsize=(7.2, altura), dpi=150, facecolor=SUPERFICIE)
    ax = fig.subplots()
    ax.set_facecolor(SUPERFICIE)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(GRADE)
    ax.tick_params(colors=TEXTO_2, labelsize=9, length=0)
    ax.set_axisbelow(True)
    return fig, ax


def titulo(ax, texto: str, subtitulo: str) -> None:
    ax.set_title(texto, loc="left", fontsize=11, color=TEXTO, fontweight="bold", pad=20)
    ax.text(0, 1.015, subtitulo, transform=ax.transAxes, fontsize=8, color=TEXTO_2, va="bottom")


def porcentagem(eixo) -> None:
    eixo.set_major_formatter(lambda v, _: f"{100 * v:.0f}%")


def afastar(posicoes: list[float], minimo: float) -> list[float]:
    ordem = sorted(range(len(posicoes)), key=posicoes.__getitem__)
    saida = list(posicoes)
    for anterior, atual in zip(ordem, ordem[1:], strict=False):
        saida[atual] = max(saida[atual], saida[anterior] + minimo)
    return saida


def rotular_finais(ax, finais: list[tuple[float, float, str]], fmt, minimo: float) -> None:
    alturas = afastar([y for _, y, _ in finais], minimo)
    for (x, y, nome), altura in zip(finais, alturas, strict=True):
        ax.text(x, altura, f"{nome} {fmt(y)}", va="center", fontsize=8.5, color=TEXTO)


def salvar(fig, saida: Path) -> None:
    saida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(saida, facecolor=SUPERFICIE, bbox_inches="tight")


def conversao_por_canal(estimativas: list[Estimativa], geral: float, saida: Path) -> None:
    ordem = sorted(estimativas, key=lambda e: e.conversao)
    fig, ax = eixos(altura=4.4)
    for y, e in enumerate(ordem):
        ax.plot(e.conversao_ic, [y, y], color=SERIES[0], lw=2, solid_capstyle="round", alpha=0.45)
        ax.plot(e.conversao, y, "o", ms=7, color=SERIES[0], mec=SUPERFICIE, mew=2)
        rotulo_x = e.conversao_ic[1] + 0.004
        ax.text(rotulo_x, y, pct(e.conversao), va="center", fontsize=8.5, color=TEXTO)
    ax.axvline(geral, color=TEXTO_2, lw=1, ls=(0, (3, 3)))
    ax.text(geral + 0.002, -0.95, f"média geral {pct(geral)}", fontsize=8, color=TEXTO_2)
    ax.set_ylim(-1.3, len(ordem) - 0.5)
    ax.set_yticks(range(len(ordem)), [f"{e.canal} ({e.contratos})" for e in ordem], color=TEXTO)
    porcentagem(ax.xaxis)
    ax.grid(axis="x", color=GRADE, lw=0.8)
    titulo(
        ax,
        "Conversão de lead em contrato, por canal",
        "ponto: estimativa com encolhimento · traço: IC 95% (bootstrap) · "
        "entre parênteses: contratos",
    )
    salvar(fig, saida)


def ativacao_por_canal(tempos: dict, canais: list[str], saida: Path) -> None:
    fig, ax = eixos(altura=3.9)
    finais = []
    for cor, canal in zip(SERIES, canais, strict=False):
        pontos = [(d, 1 - s) for d, s in curva_km(*tempos[canal]) if d <= JANELA]
        xs = [d for d, _ in pontos] + [JANELA]
        ys = [f for _, f in pontos] + [pontos[-1][1]]
        ax.step(xs, ys, where="post", color=cor, lw=2)
        finais.append((JANELA + 3, ys[-1], canal))
    rotular_finais(ax, finais, pct, 0.035)
    ax.axvline(90, color=GRADE, lw=1)
    ax.set_xlim(0, JANELA)
    ax.set_xticks(range(0, JANELA + 1, 30))
    ax.set_ylim(0, 0.75)
    porcentagem(ax.yaxis)
    ax.set_xlabel("dias desde a assinatura do contrato", fontsize=9, color=TEXTO_2)
    ax.grid(axis="y", color=GRADE, lw=0.8)
    titulo(
        ax,
        "Lojistas que já fizeram a primeira venda",
        "Kaplan-Meier, com censura em 31/08/2018 · três maiores canais",
    )
    salvar(fig, saida)


def linhas_por_mes(
    series: dict[str, dict[str, float]], titulo_: str, subtitulo: str, fmt, saida: Path
) -> None:
    fig, ax = eixos(altura=3.9)
    meses = sorted({m for valores in series.values() for m in valores})
    posicao = {m: i for i, m in enumerate(meses)}
    rotulos = []
    for cor, (nome, valores) in zip(SERIES, series.items(), strict=False):
        if not valores:
            continue
        xs = [posicao[m] for m in sorted(valores)]
        ys = [valores[m] for m in sorted(valores)]
        ax.plot(xs, ys, color=cor, lw=2, marker="o", ms=4)
        rotulos.append((xs[-1] + 0.15, ys[-1], nome))
    todos = [v for valores in series.values() for v in valores.values()]
    rotular_finais(ax, rotulos, fmt, 0.06 * (max(todos) - min(todos)))
    ax.set_xticks(range(len(meses)), [m[2:] for m in meses])
    ax.set_xlim(-0.3, len(meses) - 0.7)
    ax.yaxis.set_major_formatter(lambda v, _: fmt(v))
    ax.grid(axis="y", color=GRADE, lw=0.8)
    titulo(ax, titulo_, subtitulo)
    fig.subplots_adjust(right=0.78)
    salvar(fig, saida)
