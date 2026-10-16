from pathlib import Path

import numpy as np

from reconcile import base, graficos
from reconcile.base import numero, pct
from reconcile.valor_por_lead import JANELA, ativacao, carregar, estimar, tempos_de_ativacao

TAXAS = (0.05, 0.10, 0.15, 0.20)
MIN_CONTRATOS = 15
CABECALHO_VALOR = [
    "canal",
    "leads",
    "contratos",
    "conversão (IC 95%)",
    "vendas em 180 dias por lead (IC 95%)",
    "receita da Olist por lead, taxa de 10%",
]


def _r(valor: float) -> str:
    return base.reais(valor, casas=0)


def _intervalo(centro: str, ic: tuple[float, float], fmt) -> str:
    return f"{centro} ({fmt(ic[0])} a {fmt(ic[1])})"


def _separados(a, b) -> bool:
    return a.conversao_ic[1] < b.conversao_ic[0] or b.conversao_ic[1] < a.conversao_ic[0]


def gerar(db_path: Path, pasta: Path) -> Path:
    with base.ler(db_path) as con:
        canais, ativacoes, tempos = carregar(con), ativacao(con), tempos_de_ativacao(con)
    estimativas = estimar(canais)
    canal = {e.canal: e for e in estimativas}
    todos = next(a for a in ativacoes if a.canal == "todos")
    busca = [canal["paid_search"], canal["organic_search"]]
    fracos = [canal["social"], canal["email"]]
    sem_canal = canal["unknown"]
    receitas = next(c.receitas_180d for c in canais if c.canal == "unknown")
    total_leads = sum(e.leads for e in estimativas)
    total_contratos = sum(e.contratos for e in estimativas)
    por_contrato = estimativas[0].receita_media
    por_valor = sorted(estimativas, key=lambda e: -e.valor)
    em_90, em_janela = todos.ativado_ate[90], todos.ativado_ate[JANELA]

    img = pasta / "img"
    graficos.conversao_por_canal(
        estimativas, total_contratos / total_leads, img / "conversao_por_canal.png"
    )
    maiores = [a.canal for a in ativacoes if a.canal != "todos"][:3]
    graficos.ativacao_por_canal(tempos, maiores, img / "ativacao_por_canal.png")

    valor = [
        [
            e.canal,
            numero(e.leads),
            e.contratos,
            _intervalo(pct(e.conversao), e.conversao_ic, pct),
            _intervalo(_r(e.valor), e.valor_ic, _r),
            _r(0.10 * e.valor),
        ]
        for e in por_valor
    ]
    ativ = [
        [a.canal, a.contratos, *(pct(a.ativado_ate[d]) for d in (30, 90, JANELA))]
        for a in ativacoes
        if a.contratos >= MIN_CONTRATOS
    ]
    separados = all(_separados(b, f) for b in busca for f in fracos)
    return base.escrever(
        pasta / "growth_review.md",
        "growth_review",
        janela=JANELA,
        vezes=f"{busca[0].conversao / fracos[0].conversao:.0f}",
        sem_venda=pct(1 - em_janela),
        conv_paga=pct(busca[0].conversao),
        conv_organica=pct(busca[1].conversao),
        conv_social=pct(fracos[0].conversao),
        conv_email=pct(fracos[1].conversao),
        sobre_ic="com intervalos que não se cruzam com os de busca"
        if separados
        else "embora alguns intervalos se cruzem com os de busca",
        ativ_90=pct(em_90),
        ativ_janela=pct(em_janela),
        pontos=f"{100 * (em_janela - em_90):.0f}",
        venda_por_ativado=_r(por_contrato / max(em_janela, 1e-9)),
        leads_sem_canal=pct(sem_canal.leads / total_leads),
        contratos_sem_canal=pct(sem_canal.contratos / total_contratos),
        conv_sem_canal=pct(sem_canal.conversao),
        total_leads=numero(total_leads),
        valor=base.tabela(CABECALHO_VALOR, valor, "lrrllr"),
        media_bruta_sem_canal=_r(sem_canal.receita_media_bruta),
        concentracao=pct(receitas.max() / receitas.sum() if receitas.sum() else 0),
        mediana_sem_canal=_r(float(np.median(receitas)) if len(receitas) else 0),
        max_observados=max(e.contratos_observados for e in estimativas),
        receita_por_contrato=_r(por_contrato),
        sensibilidade=base.tabela(
            ["canal", *(f"taxa {int(100 * t)}%" for t in TAXAS)],
            [[e.canal, *(_r(t * e.valor) for t in TAXAS)] for e in por_valor[:5]],
        ),
        ativacao=base.tabela(
            ["canal", "contratos", "vendeu em 30 dias", "em 90 dias", "em 180 dias"], ativ
        ),
        total_contratos=total_contratos,
        n_canais=len(estimativas),
    )
