"""Growth Review: valor por lead, ativação e três recomendações, numa página.

Gera docs/growth_review.md e os gráficos em docs/img/. Os números saem da
camada única (marts); nada aqui recalcula métrica do contrato.
"""

from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from analysis.valor_por_lead import (  # noqa: E402
    JANELA,
    Canal,
    Estimativa,
    ativacao,
    carregar,
    curva_km,
    estimar,
    tempos_de_ativacao,
)

# Paleta de referência do guia de visualização (modo claro).
SUPERFICIE = "#fcfcfb"
TEXTO = "#0b0b0b"
TEXTO_2 = "#52514e"
GRADE = "#e4e3df"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]

TAXAS = (0.05, 0.10, 0.15, 0.20)
TAXA_PADRAO = 0.10
MIN_CONTRATOS_ATIVACAO = 15


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%".replace(".", ",")


def _r(x: float) -> str:
    return "R$ " + f"{x:,.0f}".replace(",", ".")


def _n(x: int) -> str:
    return f"{x:,}".replace(",", ".")


def _estilo(ax) -> None:
    ax.set_facecolor(SUPERFICIE)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(GRADE)
    ax.tick_params(colors=TEXTO_2, labelsize=9, length=0)


def _titulo(ax, titulo: str, subtitulo: str) -> None:
    ax.set_title(titulo, loc="left", fontsize=11, color=TEXTO, fontweight="bold", pad=20)
    ax.text(0, 1.015, subtitulo, transform=ax.transAxes, fontsize=8, color=TEXTO_2, va="bottom")


def grafico_conversao(estimativas: list[Estimativa], geral: float, saida: Path) -> None:
    ordem = sorted(estimativas, key=lambda e: e.conversao)
    fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=150, facecolor=SUPERFICIE)
    _estilo(ax)
    ys = range(len(ordem))
    for y, e in zip(ys, ordem, strict=True):
        ax.plot([e.conversao_ic[0], e.conversao_ic[1]], [y, y], color=SERIES[0], lw=2,
                solid_capstyle="round", alpha=0.45)  # fmt: skip
        ax.plot(e.conversao, y, "o", ms=7, color=SERIES[0], mec=SUPERFICIE, mew=2)
        ax.text(e.conversao_ic[1] + 0.004, y, _pct(e.conversao), va="center", fontsize=8.5,
                color=TEXTO)  # fmt: skip
    ax.axvline(geral, color=TEXTO_2, lw=1, ls=(0, (3, 3)))
    ax.text(geral + 0.002, -0.95, f"média geral {_pct(geral)}", fontsize=8, color=TEXTO_2)
    ax.set_ylim(-1.3, len(ordem) - 0.5)
    ax.set_yticks(list(ys), [f"{e.canal} ({e.contratos})" for e in ordem], color=TEXTO)
    ax.xaxis.set_major_formatter(lambda v, _: f"{100 * v:.0f}%")
    ax.grid(axis="x", color=GRADE, lw=0.8)
    ax.set_axisbelow(True)
    _titulo(ax, "Conversão de lead em contrato, por canal",
            "ponto: estimativa com encolhimento · traço: IC 95% (bootstrap) · "
            "entre parênteses: contratos")  # fmt: skip
    fig.tight_layout()
    fig.savefig(saida, facecolor=SUPERFICIE)
    plt.close(fig)


def _afastar(posicoes: list[float], minimo: float) -> list[float]:
    """Empurra rótulos para cima até ficarem a pelo menos `minimo` um do outro."""
    ordem = sorted(range(len(posicoes)), key=lambda i: posicoes[i])
    saida = list(posicoes)
    for anterior, atual in zip(ordem, ordem[1:], strict=False):
        saida[atual] = max(saida[atual], saida[anterior] + minimo)
    return saida


def grafico_ativacao(tempos: dict, canais: list[str], saida: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 3.9), dpi=150, facecolor=SUPERFICIE)
    _estilo(ax)
    limite = JANELA  # depois disso sobram poucos contratos em risco e a curva só dá saltos
    finais = []
    for cor, canal in zip(SERIES, canais, strict=False):
        t, e = tempos[canal]
        pontos = [(d, 1 - s) for d, s in curva_km(t, e) if d <= limite]
        xs, ys = [p[0] for p in pontos] + [limite], [p[1] for p in pontos] + [pontos[-1][1]]
        ax.step(xs, ys, where="post", color=cor, lw=2)
        finais.append((canal, ys[-1]))
    alturas = _afastar([y for _, y in finais], 0.035)
    for (canal, y), altura in zip(finais, alturas, strict=True):
        ax.text(limite + 3, altura, f"{canal} {_pct(y)}", va="center", fontsize=8.5,
                color=TEXTO)  # fmt: skip
    ax.axvline(90, color=GRADE, lw=1)
    ax.set_xlim(0, limite)
    ax.set_xticks([0, 30, 60, 90, 120, 150, 180])
    ax.set_ylim(0, 0.75)
    ax.yaxis.set_major_formatter(lambda v, _: f"{100 * v:.0f}%")
    ax.set_xlabel("dias desde a assinatura do contrato", fontsize=9, color=TEXTO_2)
    ax.grid(axis="y", color=GRADE, lw=0.8)
    ax.set_axisbelow(True)
    _titulo(ax, "Lojistas que já fizeram a primeira venda",
            "Kaplan-Meier, com censura em 31/08/2018 · três maiores canais")  # fmt: skip
    fig.subplots_adjust(right=0.76)
    fig.savefig(saida, facecolor=SUPERFICIE, bbox_inches="tight")
    plt.close(fig)


def _separados(a: Estimativa, b: Estimativa) -> bool:
    """Os intervalos de conversão de a e b não se cruzam."""
    return a.conversao_ic[1] < b.conversao_ic[0] or b.conversao_ic[1] < a.conversao_ic[0]


def para_markdown(
    estimativas: list[Estimativa], ativ: list, geral: float, canais: list[Canal]
) -> str:
    receitas_sem_canal = next(c.receitas_180d for c in canais if c.canal == "unknown")
    tem_receita = len(receitas_sem_canal) and receitas_sem_canal.sum() > 0
    concentracao = receitas_sem_canal.max() / receitas_sem_canal.sum() if tem_receita else 0.0
    mediana_sem_canal = float(np.median(receitas_sem_canal)) if len(receitas_sem_canal) else 0.0
    por_valor = sorted(estimativas, key=lambda e: -e.valor)
    por_canal = {e.canal: e for e in estimativas}
    a = {x.canal: x for x in ativ}
    todos = a["todos"]
    busca = [por_canal["paid_search"], por_canal["organic_search"]]
    fracos = [por_canal["social"], por_canal["email"]]
    sem_canal = por_canal["unknown"]
    total_leads = sum(e.leads for e in estimativas)
    total_contratos = sum(e.contratos for e in estimativas)
    receita_contrato = estimativas[0].receita_media  # igual para todos após o encolhimento
    separados = all(_separados(b, f) for b in busca for f in fracos)
    sobre_ic = (
        "com intervalos que não se cruzam com os de busca"
        if separados
        else "embora alguns intervalos se cruzem com os de busca"
    )

    linhas = [
        "# Growth Review",
        "",
        "Gerado por `reconcile crescimento` a partir da camada única. Não edite os números à mão.",
        "",
        "## Em uma frase",
        "",
        f"O canal decide **quantos** leads viram contrato, não **quanto** cada contrato vende: "
        f"a receita por contrato nos primeiros {JANELA} dias é a mesma em todos os canais "
        f"dentro do ruído, e um lead de busca vale cerca de "
        f"{busca[0].conversao / fracos[0].conversao:.0f} vezes um de rede social. Mas o maior "
        f"vazamento do funil não está na aquisição: {_pct(1 - todos.ativado_ate[180])} dos "
        f"lojistas contratados não fazem nenhuma venda em {JANELA} dias.",
        "",
        "## Recomendações",
        "",
        f"1. **Concentrar a verba em busca (paga e orgânica) e rever social e e-mail.** Busca "
        f"converte {_pct(busca[0].conversao)} e {_pct(busca[1].conversao)} dos leads; social "
        f"converte {_pct(fracos[0].conversao)} e e-mail {_pct(fracos[1].conversao)}, {sobre_ic}. "
        f"Como a receita por contrato não muda com o canal, a escolha do canal é uma escolha de "
        f"conversão.",
        "",
        f"2. **Tratar ativação como meta, com o mesmo peso da aquisição.** Só "
        f"{_pct(todos.ativado_ate[90])} dos contratados vendem em 90 dias e "
        f"{_pct(todos.ativado_ate[180])} em {JANELA}: a curva desacelera depois de 90 dias, "
        f"com só mais {100 * (todos.ativado_ate[180] - todos.ativado_ate[90]):.0f} pontos nos "
        "90 dias seguintes. "
        f"Um programa de onboarding nos primeiros 90 dias ataca o ponto em que o lojista "
        f"ainda pode ser recuperado. Cada contrato que ativa vende, em média, cerca de "
        f"{_r(receita_contrato / max(todos.ativado_ate[180], 1e-9))} nos primeiros {JANELA} dias.",
        "",
        f"3. **Consertar o registro de origem antes de decidir verba.** "
        f"{_pct(sem_canal.leads / total_leads)} dos leads e "
        f"{_pct(sem_canal.contratos / total_contratos)} dos contratos não têm canal "
        f"(`unknown`), e é justamente o grupo que mais converte ({_pct(sem_canal.conversao)}). "
        "Se forem leads de indicação ou de vendas internas mal registrados, o canal mais "
        "eficiente está invisível. Tornar o campo obrigatório no CRM custa pouco e destrava a "
        "recomendação 1.",
        "",
        "## Valor de um lead, por canal",
        "",
        f"Valor = P(lead vira contrato) × receita bruta média de um contrato nos {JANELA} dias "
        f"seguintes. A conversão usa os {_n(total_leads)} leads; a receita usa só os contratos "
        f"com {JANELA} dias observados por inteiro. As duas partes são encolhidas para a média "
        "geral e o intervalo vem de 2.000 reamostras (bootstrap).",
        "",
        "![Conversão por canal](img/conversao_por_canal.png)",
        "",
        "| canal | leads | contratos | conversão (IC 95%) | vendas em 180 dias por lead "
        "(IC 95%) | receita da Olist por lead, taxa de 10% |",
        "|---|---:|---:|---|---|---:|",
    ]
    for e in por_valor:
        linhas.append(
            f"| {e.canal} | {_n(e.leads)} | {e.contratos} | {_pct(e.conversao)} "
            f"({_pct(e.conversao_ic[0])} a {_pct(e.conversao_ic[1])}) | {_r(e.valor)} "
            f"({_r(e.valor_ic[0])} a {_r(e.valor_ic[1])}) | {_r(TAXA_PADRAO * e.valor)} |"
        )
    linhas += [
        "",
        "**Por que a receita por contrato é igual entre canais.** Antes do encolhimento as "
        "médias variam muito (o `unknown` tem "
        f"{_r(sem_canal.receita_media_bruta)}, mas um único lojista responde por "
        f"{_pct(concentracao)} da receita do canal e a mediana é {_r(mediana_sem_canal)}). "
        "Ainda assim, a "
        "variação entre canais é menor que a esperada só pelo acaso com tão poucos contratos "
        f"observados (de 1 a {max(e.contratos_observados for e in estimativas)} por canal). O "
        f"melhor palpite para qualquer canal é a média geral, {_r(receita_contrato)}.",
        "",
        "**Sensibilidade à taxa da Olist.** A base não informa a comissão que a Olist cobra "
        "do lojista, então a receita da Olist é uma premissa. Como ela multiplica o valor de "
        "todos os canais pelo mesmo número, a ordem dos canais não muda com a taxa; muda só o "
        "valor absoluto:",
        "",
        "| canal | " + " | ".join(f"taxa {int(100 * t)}%" for t in TAXAS) + " |",
        "|---|" + "---:|" * len(TAXAS),
    ]
    for e in por_valor[:5]:
        linhas.append(f"| {e.canal} | " + " | ".join(_r(t * e.valor) for t in TAXAS) + " |")
    linhas += [
        "",
        "## Ativação: do contrato à primeira venda",
        "",
        "![Ativação por canal](img/ativacao_por_canal.png)",
        "",
        "| canal | contratos | vendeu em 30 dias | em 90 dias | em 180 dias |",
        "|---|---:|---:|---:|---:|",
    ]
    for x in ativ:
        if x.contratos >= MIN_CONTRATOS_ATIVACAO:
            linhas.append(
                f"| {x.canal} | {x.contratos} | {_pct(x.ativado_ate[30])} | "
                f"{_pct(x.ativado_ate[90])} | {_pct(x.ativado_ate[180])} |"
            )
    linhas += [
        "",
        f"Canais com menos de {MIN_CONTRATOS_ATIVACAO} contratos ficam fora da tabela. As "
        "frações usam Kaplan-Meier: contrato assinado perto do fim da base conta enquanto foi "
        'observado e sai da conta depois, em vez de entrar como "nunca vendeu".',
        "",
        "## Premissas e limites",
        "",
        f"- **Janela de {JANELA} dias.** Nenhum contrato tem 12 meses observados (o mais antigo é "
        "de dez/2017 e a observação termina em 31/08/2018).",
        "- **Receita é a do lojista (GMV), não a da Olist.** A receita da Olist depende da taxa, "
        "que é premissa.",
        "- **Correlação, não efeito causal.** Um canal que converte mais pode atrair lojistas "
        "diferentes; o que a análise sustenta é de onde os contratos vieram, não o que "
        "aconteceria mudando a verba.",
        f"- **Pouca amostra em canais pequenos.** {total_contratos} contratos em "
        f"{len(estimativas)} canais; por isso o encolhimento e os intervalos.",
        "",
    ]
    return "\n".join(linhas)


def gerar(db_path: Path, pasta_docs: Path) -> Path:
    with duckdb.connect(str(db_path), read_only=True) as con:
        canais = carregar(con)
        estimativas = estimar(canais)
        ativ = ativacao(con)
        tempos = tempos_de_ativacao(con)

    geral = sum(c.contratos for c in canais) / sum(c.leads for c in canais)
    img = pasta_docs / "img"
    img.mkdir(parents=True, exist_ok=True)
    grafico_conversao(estimativas, geral, img / "conversao_por_canal.png")
    maiores = [x.canal for x in ativ if x.canal != "todos"][:3]
    grafico_ativacao(tempos, maiores, img / "ativacao_por_canal.png")

    saida = pasta_docs / "growth_review.md"
    texto = para_markdown(estimativas, ativ, geral, canais)
    saida.write_text(texto, encoding="utf-8", newline="\n")
    return saida
