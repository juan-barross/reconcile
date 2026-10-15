"""Growth Review: valor por lead, ativação e três recomendações, numa página."""

from dataclasses import dataclass
from pathlib import Path

import duckdb
import numpy as np

from analysis import graficos
from analysis.valor_por_lead import (
    JANELA,
    Ativacao,
    Canal,
    Estimativa,
    ativacao,
    carregar,
    estimar,
    tempos_de_ativacao,
)
from ingest.formato import numero, pct, reais

TAXAS = (0.05, 0.10, 0.15, 0.20)
TAXA_PADRAO = 0.10
MIN_CONTRATOS_ATIVACAO = 15


def _r(valor: float) -> str:
    return reais(valor, casas=0)


@dataclass(frozen=True)
class Fatos:
    estimativas: list[Estimativa]
    ativacoes: list[Ativacao]
    concentracao_sem_canal: float  # fatia do maior lojista na receita do canal unknown
    mediana_sem_canal: float

    def canal(self, nome: str) -> Estimativa:
        return next(e for e in self.estimativas if e.canal == nome)

    @property
    def todos(self) -> Ativacao:
        return next(a for a in self.ativacoes if a.canal == "todos")

    @property
    def total_leads(self) -> int:
        return sum(e.leads for e in self.estimativas)

    @property
    def total_contratos(self) -> int:
        return sum(e.contratos for e in self.estimativas)

    @property
    def receita_por_contrato(self) -> float:
        # Depois do encolhimento a média é a mesma para todos os canais.
        return self.estimativas[0].receita_media


def _fatos(canais: list[Canal], estimativas: list[Estimativa], ativacoes: list) -> Fatos:
    receitas = next(c.receitas_180d for c in canais if c.canal == "unknown")
    soma = receitas.sum() if len(receitas) else 0.0
    return Fatos(
        estimativas,
        ativacoes,
        concentracao_sem_canal=receitas.max() / soma if soma else 0.0,
        mediana_sem_canal=float(np.median(receitas)) if len(receitas) else 0.0,
    )


def _ics_separados(a: Estimativa, b: Estimativa) -> bool:
    return a.conversao_ic[1] < b.conversao_ic[0] or b.conversao_ic[1] < a.conversao_ic[0]


def _resumo_e_recomendacoes(f: Fatos) -> list[str]:
    busca = [f.canal("paid_search"), f.canal("organic_search")]
    fracos = [f.canal("social"), f.canal("email")]
    sem_canal = f.canal("unknown")
    em_90, em_janela = f.todos.ativado_ate[90], f.todos.ativado_ate[JANELA]
    separados = all(_ics_separados(b, x) for b in busca for x in fracos)
    sobre_ic = (
        "com intervalos que não se cruzam com os de busca"
        if separados
        else "embora alguns intervalos se cruzem com os de busca"
    )
    return [
        "## Em uma frase",
        "",
        "O canal decide **quantos** leads viram contrato, não **quanto** cada contrato vende: "
        f"a receita por contrato nos primeiros {JANELA} dias é a mesma em todos os canais "
        "dentro do ruído, e um lead de busca vale cerca de "
        f"{busca[0].conversao / fracos[0].conversao:.0f} vezes um de rede social. Mas o maior "
        f"vazamento do funil não está na aquisição: {pct(1 - em_janela)} dos "
        f"lojistas contratados não fazem nenhuma venda em {JANELA} dias.",
        "",
        "## Recomendações",
        "",
        "1. **Concentrar a verba em busca (paga e orgânica) e rever social e e-mail.** Busca "
        f"converte {pct(busca[0].conversao)} e {pct(busca[1].conversao)} dos leads; social "
        f"converte {pct(fracos[0].conversao)} e e-mail {pct(fracos[1].conversao)}, {sobre_ic}. "
        "Como a receita por contrato não muda com o canal, a escolha do canal é uma escolha de "
        "conversão.",
        "",
        "2. **Tratar ativação como meta, com o mesmo peso da aquisição.** Só "
        f"{pct(em_90)} dos contratados vendem em 90 dias e "
        f"{pct(em_janela)} em {JANELA}: a curva desacelera depois de 90 dias, "
        f"com só mais {100 * (em_janela - em_90):.0f} pontos nos 90 dias seguintes. "
        "Um programa de onboarding nos primeiros 90 dias ataca o ponto em que o lojista "
        "ainda pode ser recuperado. Cada contrato que ativa vende, em média, cerca de "
        f"{_r(f.receita_por_contrato / max(em_janela, 1e-9))} nos primeiros {JANELA} dias.",
        "",
        "3. **Consertar o registro de origem antes de decidir verba.** "
        f"{pct(sem_canal.leads / f.total_leads)} dos leads e "
        f"{pct(sem_canal.contratos / f.total_contratos)} dos contratos não têm canal "
        f"(`unknown`), e é justamente o grupo que mais converte ({pct(sem_canal.conversao)}). "
        "Se forem leads de indicação ou de vendas internas mal registrados, o canal mais "
        "eficiente está invisível. Tornar o campo obrigatório no CRM custa pouco e destrava a "
        "recomendação 1.",
        "",
    ]


def _valor_por_lead(f: Fatos) -> list[str]:
    por_valor = sorted(f.estimativas, key=lambda e: -e.valor)
    sem_canal = f.canal("unknown")
    linhas = [
        "## Valor de um lead, por canal",
        "",
        f"Valor = P(lead vira contrato) × receita bruta média de um contrato nos {JANELA} dias "
        f"seguintes. A conversão usa os {numero(f.total_leads)} leads; a receita usa só os "
        f"contratos com {JANELA} dias observados por inteiro. As duas partes são encolhidas "
        "para a média geral e o intervalo vem de 2.000 reamostras (bootstrap).",
        "",
        "![Conversão por canal](img/conversao_por_canal.png)",
        "",
        "| canal | leads | contratos | conversão (IC 95%) | vendas em 180 dias por lead "
        "(IC 95%) | receita da Olist por lead, taxa de 10% |",
        "|---|---:|---:|---|---|---:|",
    ]
    linhas += [
        f"| {e.canal} | {numero(e.leads)} | {e.contratos} | {pct(e.conversao)} "
        f"({pct(e.conversao_ic[0])} a {pct(e.conversao_ic[1])}) | {_r(e.valor)} "
        f"({_r(e.valor_ic[0])} a {_r(e.valor_ic[1])}) | {_r(TAXA_PADRAO * e.valor)} |"
        for e in por_valor
    ]
    linhas += [
        "",
        "**Por que a receita por contrato é igual entre canais.** Antes do encolhimento as "
        f"médias variam muito (o `unknown` tem {_r(sem_canal.receita_media_bruta)}, mas um "
        f"único lojista responde por {pct(f.concentracao_sem_canal)} da receita do canal e a "
        f"mediana é {_r(f.mediana_sem_canal)}). Ainda assim, a variação entre canais é menor "
        "que a esperada só pelo acaso com tão poucos contratos observados (de 1 a "
        f"{max(e.contratos_observados for e in f.estimativas)} por canal). O melhor palpite "
        f"para qualquer canal é a média geral, {_r(f.receita_por_contrato)}.",
        "",
        "**Sensibilidade à taxa da Olist.** A base não informa a comissão que a Olist cobra "
        "do lojista, então a receita da Olist é uma premissa. Como ela multiplica o valor de "
        "todos os canais pelo mesmo número, a ordem dos canais não muda com a taxa; muda só o "
        "valor absoluto:",
        "",
        "| canal | " + " | ".join(f"taxa {int(100 * t)}%" for t in TAXAS) + " |",
        "|---|" + "---:|" * len(TAXAS),
        *(
            f"| {e.canal} | " + " | ".join(_r(t * e.valor) for t in TAXAS) + " |"
            for e in por_valor[:5]
        ),
        "",
    ]
    return linhas


def _ativacao(f: Fatos) -> list[str]:
    return [
        "## Ativação: do contrato à primeira venda",
        "",
        "![Ativação por canal](img/ativacao_por_canal.png)",
        "",
        "| canal | contratos | vendeu em 30 dias | em 90 dias | em 180 dias |",
        "|---|---:|---:|---:|---:|",
        *(
            f"| {a.canal} | {a.contratos} | {pct(a.ativado_ate[30])} | "
            f"{pct(a.ativado_ate[90])} | {pct(a.ativado_ate[JANELA])} |"
            for a in f.ativacoes
            if a.contratos >= MIN_CONTRATOS_ATIVACAO
        ),
        "",
        f"Canais com menos de {MIN_CONTRATOS_ATIVACAO} contratos ficam fora da tabela. As "
        "frações usam Kaplan-Meier: contrato assinado perto do fim da base conta enquanto foi "
        'observado e sai da conta depois, em vez de entrar como "nunca vendeu".',
        "",
    ]


def _premissas(f: Fatos) -> list[str]:
    return [
        "## Premissas e limites",
        "",
        f"- **Janela de {JANELA} dias.** Nenhum contrato tem 12 meses observados (o mais antigo é "
        "de dez/2017 e a observação termina em 31/08/2018).",
        "- **Receita é a do lojista (GMV), não a da Olist.** A receita da Olist depende da taxa, "
        "que é premissa.",
        "- **Correlação, não efeito causal.** Um canal que converte mais pode atrair lojistas "
        "diferentes; o que a análise sustenta é de onde os contratos vieram, não o que "
        "aconteceria mudando a verba.",
        f"- **Pouca amostra em canais pequenos.** {f.total_contratos} contratos em "
        f"{len(f.estimativas)} canais; por isso o encolhimento e os intervalos.",
        "",
    ]


def para_markdown(f: Fatos) -> str:
    cabecalho = [
        "# Growth Review",
        "",
        "Gerado por `reconcile crescimento` a partir da camada única. Não edite os números à mão.",
        "",
    ]
    secoes = (_resumo_e_recomendacoes, _valor_por_lead, _ativacao, _premissas)
    return "\n".join(cabecalho + [linha for secao in secoes for linha in secao(f)])


def gerar(db_path: Path, pasta_docs: Path) -> Path:
    with duckdb.connect(str(db_path), read_only=True) as con:
        canais = carregar(con)
        ativacoes = ativacao(con)
        tempos = tempos_de_ativacao(con)
    fatos = _fatos(canais, estimar(canais), ativacoes)

    img = pasta_docs / "img"
    img.mkdir(parents=True, exist_ok=True)
    geral = fatos.total_contratos / fatos.total_leads
    graficos.conversao_por_canal(fatos.estimativas, geral, img / "conversao_por_canal.png")
    maiores = [a.canal for a in ativacoes if a.canal != "todos"][:3]
    graficos.ativacao_por_canal(tempos, maiores, img / "ativacao_por_canal.png")

    saida = pasta_docs / "growth_review.md"
    saida.write_text(para_markdown(fatos), encoding="utf-8", newline="\n")
    return saida
