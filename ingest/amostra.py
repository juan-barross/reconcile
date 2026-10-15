"""Amostra sintética no formato exato dos CSVs da Olist.

Usada pelos testes e pela CI, que não podem redistribuir o dado real. Os valores
são inventados e as anomalias são plantadas em quantidade conhecida (PLANTADAS).
"""

import csv
from datetime import datetime, timedelta
from pathlib import Path

from ingest.fontes import FONTES

PLANTADAS = {
    "customer_id a mais que pessoas (customer_unique_id)": 4,
    "pedidos sem nenhum item": 2,
    "pedidos sem pagamento": 1,
    "contratos cujo lojista nunca vendeu": 2,
    "envio à transportadora antes da compra": 1,
    "linhas de avaliação que repetem um review_id": 1,
    "leads sem origem (nula)": 1,
    "leads com origem 'unknown'": 1,
    "pedidos pagos a mais que itens + frete (> R$ 1)": 3,
    "pagamentos com valor zero": 1,
    "produtos sem categoria": 1,
}

_COLUNAS = {
    "customers": "customer_id customer_unique_id customer_zip_code_prefix customer_city "
    "customer_state",
    "geolocation": "geolocation_zip_code_prefix geolocation_lat geolocation_lng "
    "geolocation_city geolocation_state",
    "orders": "order_id customer_id order_status order_purchase_timestamp order_approved_at "
    "order_delivered_carrier_date order_delivered_customer_date order_estimated_delivery_date",
    "order_items": "order_id order_item_id product_id seller_id shipping_limit_date price "
    "freight_value",
    "order_payments": "order_id payment_sequential payment_type payment_installments payment_value",
    "order_reviews": "review_id order_id review_score review_comment_title "
    "review_comment_message review_creation_date review_answer_timestamp",
    "products": "product_id product_category_name product_name_lenght "
    "product_description_lenght product_photos_qty product_weight_g product_length_cm "
    "product_height_cm product_width_cm",
    "sellers": "seller_id seller_zip_code_prefix seller_city seller_state",
    "product_category_translation": "product_category_name product_category_name_english",
    "marketing_qualified_leads": "mql_id first_contact_date landing_page_id origin",
    "closed_deals": "mql_id seller_id sdr_id sr_id won_date business_segment lead_type "
    "lead_behaviour_profile has_company has_gtin average_stock business_type "
    "declared_product_catalog_size declared_monthly_revenue",
}
CABECALHOS = {tabela: colunas.split() for tabela, colunas in _COLUNAS.items()}

INICIO_FUNIL = datetime(2017, 11, 1)  # todo contrato é anterior à primeira venda
INICIO_VENDAS = datetime(2018, 1, 1, 10)
N_PEDIDOS = 30

PEDIDO_ENVIO_ANTES_DA_COMPRA = 3
PEDIDO_SEM_PAGAMENTO = 7  # barato, como no dado real
PEDIDOS_COM_JUROS = (5, 10, 15)
PEDIDO_COM_VOUCHER_ZERADO = 12
PEDIDOS_CANCELADOS_COM_ITENS = (27, 28)
PEDIDOS_SEM_ITENS = {29: "unavailable", 30: "canceled"}
# Recompra em pedido válido: sem isso, trocar a chave de cliente para
# customer_id não mudaria nenhum número e passaria despercebido.
CLIENTES_QUE_VOLTAM = range(21, 25)

FMT = "%Y-%m-%d %H:%M:%S"


def _ts(d: datetime | None) -> str:
    return d.strftime(FMT) if d else ""


def _dia(d: datetime) -> str:
    return d.strftime("%Y-%m-%d 00:00:00")


def _catalogo(t: dict) -> None:
    t["product_category_translation"] += [
        ["beleza_saude", "health_beauty"],
        ["esporte_lazer", "sports_leisure"],
        ["informatica_acessorios", "computers_accessories"],
    ]
    categorias = ["beleza_saude", "esporte_lazer", "informatica_acessorios", "beleza_saude", ""]
    for i, categoria in enumerate(categorias, 1):
        t["products"].append([f"p{i}", categoria, "40", "300", "2", "500", "20", "10", "15"])
    for i in range(1, 5):
        t["sellers"].append([f"s{i}", f"0{i}000", "sao paulo", "SP"])
        t["geolocation"].append([f"0{i}000", "-23.5", "-46.6", "sao paulo", "SP"])


def _funil(t: dict) -> None:
    origens = "organic_search paid_search social organic_search email paid_search - unknown "
    origens += "referral direct_traffic"
    for i, origem in enumerate(origens.split(), 1):
        contato = (INICIO_FUNIL + timedelta(days=7 * i)).date().isoformat()
        t["marketing_qualified_leads"].append(
            [f"m{i:02d}", contato, f"lp{i % 3}", "" if origem == "-" else origem]
        )
    # s5 e s6 assinam e nunca vendem.
    for n, seller, dias in [(1, "s1", 10), (2, "s2", 12), (3, "s5", 30), (4, "s6", 40)]:
        fechado = INICIO_FUNIL + timedelta(days=7 * n + dias, hours=14)
        t["closed_deals"].append(
            [f"m{n:02d}", seller, "sdr1", "sr1", _ts(fechado), "health_beauty",
             "online_medium", "cat", "", "", "", "reseller", "", "0.0"]
        )  # fmt: skip


def _clientes(t: dict) -> None:
    for i in range(1, N_PEDIDOS + 1):
        pessoa = i - 20 if i in CLIENTES_QUE_VOLTAM else i
        t["customers"].append([f"c{i:02d}", f"u{pessoa:02d}", "01000", "sao paulo", "SP"])


def _pagamentos(pedido: str, i: int, total: float) -> list[list[str]]:
    if i in PEDIDOS_SEM_ITENS:
        return [[pedido, "1", "credit_card", "1", "80.00"]]
    if i == PEDIDO_SEM_PAGAMENTO:
        return []
    if i in PEDIDOS_COM_JUROS:
        return [[pedido, "1", "credit_card", "6", f"{total * 1.02:.2f}"]]
    if i == PEDIDO_COM_VOUCHER_ZERADO:
        return [
            [pedido, "1", "credit_card", "1", f"{total:.2f}"],
            [pedido, "2", "voucher", "1", "0.00"],
        ]
    return [[pedido, "1", "boleto", "1", f"{total:.2f}"]]


def _pedidos(t: dict) -> None:
    for i in range(1, N_PEDIDOS + 1):
        pedido = f"o{i:02d}"
        compra = INICIO_VENDAS + timedelta(days=5 * i)
        status, envio, entrega = "delivered", compra + timedelta(days=1), compra + timedelta(6)
        if i == PEDIDO_ENVIO_ANTES_DA_COMPRA:
            envio = compra - timedelta(days=1)
        if i in PEDIDOS_CANCELADOS_COM_ITENS:
            status, envio, entrega = "canceled", None, None
        if i in PEDIDOS_SEM_ITENS:
            status, envio, entrega = PEDIDOS_SEM_ITENS[i], None, None
        t["orders"].append(
            [pedido, f"c{i:02d}", status, _ts(compra), _ts(compra + timedelta(hours=2)),
             _ts(envio), _ts(entrega), _dia(compra + timedelta(days=15))]
        )  # fmt: skip

        total = 0.0
        if i not in PEDIDOS_SEM_ITENS:
            preco, frete = (15, 5) if i == PEDIDO_SEM_PAGAMENTO else (200 + i, 10)
            for item in range(1, 3 if i % 4 == 0 else 2):
                total += preco + frete
                t["order_items"].append(
                    [pedido, str(item), f"p{(i + item) % 5 + 1}", f"s{(i + item) % 4 + 1}",
                     _ts(compra + timedelta(days=3)), f"{preco:.2f}", f"{frete:.2f}"]
                )  # fmt: skip
        t["order_payments"] += _pagamentos(pedido, i, total)

        if status == "delivered":
            review = "r01" if i in (1, 2) else f"r{i:02d}"  # o mesmo review_id em dois pedidos
            t["order_reviews"].append(
                [review, pedido, str(i % 5 + 1), "", "", _dia(compra + timedelta(days=7)),
                 _ts(compra + timedelta(days=8))]
            )  # fmt: skip


def gerar() -> dict[str, list[list[str]]]:
    tabelas: dict[str, list[list[str]]] = {nome: [] for nome in CABECALHOS}
    for parte in (_catalogo, _funil, _clientes, _pedidos):
        parte(tabelas)
    return tabelas


def escrever(destino: Path) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    tabelas = gerar()
    caminhos = []
    for fonte in FONTES:
        caminho = destino / fonte.arquivo
        with caminho.open("w", newline="", encoding="utf-8") as f:
            escritor = csv.writer(f)
            escritor.writerow(CABECALHOS[fonte.tabela])
            escritor.writerows(tabelas[fonte.tabela])
        caminhos.append(caminho)
    return caminhos
