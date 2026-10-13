"""Auditoria da camada raw: o que a origem tem de estranho antes de qualquer modelo.

Cada checagem é uma consulta que devolve um número. O número vai para
docs/auditoria.md junto com a leitura de negócio, para que a decisão tomada
no staging e no intermediate tenha uma origem rastreável.
"""

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb

from ingest.fontes import DB_PATH


@dataclass(frozen=True)
class Checagem:
    categoria: str
    nome: str
    sql: str
    leitura: str


def _dup(tabela: str, chave: str) -> str:
    return f"select count(*) - count(distinct ({chave})) from raw.{tabela}"


def _orfao(filho: str, pai: str, chave: str) -> str:
    return (
        f"select count(*) from raw.{filho} f "
        f"where not exists (select 1 from raw.{pai} p where p.{chave} = f.{chave})"
    )


CHECAGENS: tuple[Checagem, ...] = (
    # Chaves
    Checagem("chave", "pedidos com order_id repetido", _dup("orders", "order_id"), "Chave limpa."),
    Checagem(
        "chave",
        "itens com (pedido, número do item) repetido",
        _dup("order_items", "order_id, order_item_id"),
        "Chave composta limpa.",
    ),
    Checagem(
        "chave",
        "pagamentos com (pedido, sequência) repetido",
        _dup("order_payments", "order_id, payment_sequential"),
        "Chave composta limpa.",
    ),
    Checagem(
        "chave",
        "linhas de avaliação que repetem um review_id",
        _dup("order_reviews", "review_id"),
        "A mesma avaliação aparece em mais de um pedido. A chave é (review_id, order_id).",
    ),
    Checagem(
        "chave",
        "leads com mql_id repetido",
        _dup("marketing_qualified_leads", "mql_id"),
        "Cada lead tem uma linha, logo uma origem só.",
    ),
    Checagem(
        "chave",
        "contratos com mql_id repetido",
        _dup("closed_deals", "mql_id"),
        "Cada lead fecha no máximo um contrato.",
    ),
    # Clientes
    Checagem(
        "cliente",
        "customer_id a mais que pessoas (customer_unique_id)",
        "select count(distinct customer_id) - count(distinct customer_unique_id) "
        "from raw.customers",
        "Cada pedido gera um customer_id novo. Contar por customer_id infla clientes.",
    ),
    Checagem(
        "cliente",
        "pessoas com mais de um customer_id",
        "select count(*) from (select customer_unique_id from raw.customers "
        "group by 1 having count(*) > 1)",
        "Clientes que voltaram a comprar. Contados uma vez por pedido se a chave for errada.",
    ),
    # Órfãos
    Checagem(
        "órfão",
        "itens sem pedido",
        _orfao("order_items", "orders", "order_id"),
        "Integridade ok.",
    ),
    Checagem(
        "órfão",
        "pagamentos sem pedido",
        _orfao("order_payments", "orders", "order_id"),
        "Integridade ok.",
    ),
    Checagem(
        "órfão",
        "pedidos sem nenhum item",
        _orfao("orders", "order_items", "order_id"),
        "Quase todos cancelados ou indisponíveis. Entram na contagem de pedidos de "
        "quem conta pela tabela de pedidos e somem para quem conta por itens.",
    ),
    Checagem(
        "órfão",
        "pedidos sem pagamento",
        _orfao("orders", "order_payments", "order_id"),
        "Pedido sem registro de pagamento: some da receita do financeiro.",
    ),
    Checagem(
        "órfão",
        "contratos sem lead de origem",
        _orfao("closed_deals", "marketing_qualified_leads", "mql_id"),
        "Todo contrato veio de um lead do marketing.",
    ),
    Checagem(
        "órfão",
        "contratos cujo lojista nunca vendeu",
        "select count(*) from raw.closed_deals d where not exists "
        "(select 1 from raw.order_items i where i.seller_id = d.seller_id)",
        "Contrato assinado que não virou lojista ativo. Vendas conta, operação não.",
    ),
    # Datas
    Checagem(
        "data",
        "envio à transportadora antes da compra",
        "select count(*) from raw.orders "
        "where order_delivered_carrier_date < order_purchase_timestamp",
        "Data impossível. Afeta quem conta vendas pela data de envio.",
    ),
    Checagem(
        "data",
        "entrega ao cliente antes do envio à transportadora",
        "select count(*) from raw.orders "
        "where order_delivered_customer_date < order_delivered_carrier_date",
        "Data impossível. Afeta prazo de entrega, não receita.",
    ),
    Checagem(
        "data",
        "entregues ou enviados sem data de aprovação",
        "select count(*) from raw.orders where order_approved_at is null "
        "and order_status in ('delivered', 'shipped')",
        "Somem de quem conta pela data de aprovação, apesar de terem sido entregues.",
    ),
    Checagem(
        "data",
        "status 'delivered' sem data de entrega",
        "select count(*) from raw.orders where order_status = 'delivered' "
        "and order_delivered_customer_date is null",
        "Somem de quem conta pela data de entrega.",
    ),
    Checagem(
        "data",
        "cancelados com data de entrega",
        "select count(*) from raw.orders where order_status = 'canceled' "
        "and order_delivered_customer_date is not null",
        "Status e datas se contradizem. Quem filtra por data de entrega conta como venda.",
    ),
    Checagem(
        "data",
        "contrato fechado antes do primeiro contato",
        "select count(*) from raw.closed_deals d join raw.marketing_qualified_leads m "
        "using (mql_id) where cast(d.won_date as timestamp) < cast(m.first_contact_date as date)",
        "Data impossível no funil.",
    ),
    Checagem(
        "data",
        "contratos fechados depois do último pedido da base",
        "select count(*) from raw.closed_deals where cast(won_date as timestamp) > "
        "(select max(cast(order_purchase_timestamp as timestamp)) from raw.orders)",
        "Não tiveram como vender dentro da base. Entram no denominador da ativação "
        "e puxam a taxa para baixo se ninguém tratar.",
    ),
    # Funil e pagamentos
    Checagem(
        "funil",
        "leads sem origem (nula)",
        "select count(*) from raw.marketing_qualified_leads where origin is null",
        "Somados a 'unknown' na análise por canal.",
    ),
    Checagem(
        "funil",
        "leads com origem 'unknown'",
        "select count(*) from raw.marketing_qualified_leads where origin = 'unknown'",
        "Canal desconhecido. Não dá para atribuir receita a um canal.",
    ),
    Checagem(
        "pagamento",
        "pagamentos com valor zero",
        "select count(*) from raw.order_payments where cast(payment_value as decimal(12,2)) = 0",
        "Vouchers zerados e 'not_defined'. Não mudam a receita, mas contam como pagamento.",
    ),
    Checagem(
        "pagamento",
        "pedidos pagos a mais que itens + frete (> R$ 1)",
        """
        with pago as (
            select order_id, sum(cast(payment_value as decimal(12,2))) as v
            from raw.order_payments group by 1
        ), itens as (
            select order_id,
                   sum(cast(price as decimal(12,2)) + cast(freight_value as decimal(12,2))) as v
            from raw.order_items group by 1
        )
        select count(*) from pago join itens using (order_id) where pago.v - itens.v > 1
        """,
        "Em geral juros de parcelamento. É a diferença entre a receita do financeiro "
        "e a do comercial.",
    ),
    Checagem(
        "produto",
        "produtos sem categoria",
        "select count(*) from raw.products where product_category_name is null",
        "Ficam como 'sem categoria' em qualquer corte por categoria.",
    ),
)


def linhas_por_tabela(con: duckdb.DuckDBPyConnection) -> list[tuple[str, int]]:
    return con.execute(
        """
        select tabela, linhas from raw._cargas
        qualify row_number() over (partition by tabela order by carregado_em desc) = 1
        order by tabela
        """
    ).fetchall()


def rodar(db_path: Path = DB_PATH) -> list[tuple[Checagem, int]]:
    with duckdb.connect(str(db_path), read_only=True) as con:
        return [(c, con.execute(c.sql).fetchone()[0]) for c in CHECAGENS]


def _n(x: int) -> str:
    return f"{x:,}".replace(",", ".")


def para_markdown(resultados: list[tuple[Checagem, int]], linhas: list[tuple[str, int]]) -> str:
    partes = [
        "# Auditoria da camada raw",
        "",
        f"Gerado por `reconcile auditar` em {date.today().isoformat()}. Não edite à mão.",
        "",
        "## Linhas por tabela",
        "",
        "| tabela | linhas |",
        "|---|---:|",
        *[f"| `{t}` | {_n(n)} |" for t, n in linhas],
        "",
        "## Checagens",
        "",
        "| categoria | checagem | resultado | leitura |",
        "|---|---|---:|---|",
        *[f"| {c.categoria} | {c.nome} | {_n(n)} | {c.leitura} |" for c, n in resultados],
        "",
    ]
    return "\n".join(partes)


def auditar(db_path: Path = DB_PATH, saida: Path = Path("docs/auditoria.md")) -> Path:
    resultados = rodar(db_path)
    with duckdb.connect(str(db_path), read_only=True) as con:
        linhas = linhas_por_tabela(con)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(para_markdown(resultados, linhas), encoding="utf-8", newline="\n")
    return saida
