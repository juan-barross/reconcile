from pathlib import Path

from reconcile import base, pontes
from reconcile.base import numero as n
from reconcile.base import reais


def _fracao(parte: float, todo: float) -> str:
    return base.pct(parte / todo, 0) if todo else base.TRACO


def _ponte_receita(p: dict) -> str:
    corpo = [
        ["**vendas** (itens + frete, data da compra)", f"**{reais(p['vendas'])}**"],
        *([nome, reais(v, sinal=True)] for nome, v in pontes.componentes(p) if v),
        ["**financeiro** (pagamentos, data de aprovação)", f"**{reais(p['financeiro'])}**"],
    ]
    return base.tabela(["", "R$"], corpo)


def gerar(db_path: Path, saida: Path, mes: str) -> Path:
    with base.ler(db_path) as con:
        r = pontes.respostas(con)
        loj, lm = pontes.ponte_lojistas(con), pontes.ponte_lojistas_mes(con, mes)
        cli, rec, rec_mes = (
            pontes.ponte_clientes(con),
            pontes.ponte_receita(con),
            pontes.ponte_receita(con, mes),
        )
        oficial = pontes.camada_unica(con, mes)
    m = base.mes_extenso(mes)

    def resposta(area: str, pergunta: str, fmt=n) -> str:
        return fmt(pontes.total(r, area, pergunta, mes))

    pauta = [
        [p, *(resposta(a, p, fmt) for a in pontes.AREAS)]
        for p, fmt in [("lojistas conquistados", n), ("clientes novos", n), ("receita", reais)]
    ]
    lojistas_mes = [
        ["**marketing** (mês do primeiro contato)", f"**{n(lm['marketing'])}**"],
        [f"contato em {m}, contrato fechado em outro mês", f"− {n(lm['contato_fechou_em_outro'])}"],
        [f"contrato fechado em {m}, contato em outro mês", f"+ {n(lm['fechou_contato_em_outro'])}"],
        ["**vendas** (mês do fechamento)", f"**{n(lm['vendas'])}**"],
        [f"fechou em {m} e nunca vendeu", f"− {n(lm['fechou_nunca_vendeu'])}"],
        [f"fechou em {m} e só vendeu num mês seguinte", f"− {n(lm['fechou_vendeu_depois'])}"],
        [f"fechou antes e fez a primeira venda em {m}", f"+ {n(lm['fechou_antes_vendeu_no_mes'])}"],
        ["**operação** (mês da primeira venda)", f"**{n(lm['operacao'])}**"],
    ]
    lojistas_base = [
        [
            "primeiro contato e fechamento em meses diferentes",
            f"{n(loj['fora_do_mes'])} de {n(loj['contratos'])} "
            f"({_fracao(loj['fora_do_mes'], loj['contratos'])})",
            "marketing contra vendas, mês a mês",
        ],
        [
            "contrato assinado, lojista nunca vendeu",
            f"{n(loj['nunca_venderam'])} ({_fracao(loj['nunca_venderam'], loj['contratos'])})",
            "vendas contra operação",
        ],
        [
            "... dos quais fecharam depois do último pedido da base",
            n(loj["fechados_depois_da_base"]),
            "operação não tinha como contar",
        ],
    ]
    regras = [
        ("lojistas contratados", n(oficial["lojistas_contratados"]), "data do contrato"),
        (
            "lojistas ativados",
            n(oficial["lojistas_ativados"]),
            "primeira venda válida, no mês dela",
        ),
        (
            "clientes novos",
            n(oficial["clientes_novos"]),
            "pessoa (`customer_unique_id`), primeira compra válida",
        ),
        (
            "pedidos válidos",
            n(oficial["pedidos_validos"]),
            "sem cancelados, indisponíveis ou pedidos sem item",
        ),
        ("receita bruta", reais(oficial["receita_bruta"]), "itens + frete, data da compra"),
        (
            "receita paga",
            reais(oficial["receita_paga"]),
            "pagamentos, data de aprovação (reserva: compra)",
        ),
        ("ticket médio", reais(oficial["ticket_medio"]), "receita bruta ÷ pedidos válidos"),
    ]
    return base.escrever(
        saida,
        "a_reuniao",
        m=m,
        pauta=base.tabela(["pergunta", "marketing", "vendas", "financeiro", "operação"], pauta),
        loj_marketing=resposta("marketing", "lojistas conquistados"),
        loj_vendas=resposta("vendas", "lojistas conquistados"),
        loj_operacao=resposta("operacao", "lojistas conquistados"),
        contratos=n(loj["contratos"]),
        venderam=n(loj["venderam"]),
        lojistas_mes=base.tabela(["", "lojistas"], lojistas_mes),
        lojistas_base=base.tabela(["causa", "lojistas", "quem é afetado"], lojistas_base, "lrl"),
        mediana=n(loj["mediana_dias"]),
        nunca_venderam=n(loj["nunca_venderam"]),
        customer_ids=n(cli["customer_ids"]),
        pessoas=n(cli["pessoas"]),
        contados_a_mais=n(cli["contados_a_mais"]),
        pessoas_que_voltaram=n(cli["pessoas_que_voltaram"]),
        cli_marketing=resposta("marketing", "clientes novos"),
        cli_operacao=resposta("operacao", "clientes novos"),
        clientes=base.tabela(
            ["causa", "clientes"],
            [
                [
                    "pedidos de quem já tinha comprado antes, contados como cliente novo",
                    n(cli["contados_a_mais"]),
                ]
            ],
        ),
        receita=_ponte_receita(rec),
        pago_sem_item=reais(rec["pago_sem_item"]),
        pago_a_mais=reais(rec["pago_a_mais"]),
        pago_a_mais_pedidos=n(rec["pago_a_mais_pedidos"]),
        pago_a_mais_parcelados=n(rec["pago_a_mais_parcelados"]),
        cancelados_vendas=reais(rec["cancelados_vendas"]),
        cancelados_financeiro=reais(rec["cancelados_financeiro"]),
        receita_mes=_ponte_receita(rec_mes),
        camada_unica=base.tabela(["métrica", m, "regra (ver contrato)"], regras, "lrl"),
    )
