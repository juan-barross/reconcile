"""Amostra sintética no formato exato dos CSVs da Olist.

Serve para três coisas: os testes rodarem sem rede, a CI rodar `dbt build` sem
redistribuir o dado real (a licença não permite) e quem avalia o projeto ver o
pipeline inteiro em segundos.

Os valores são inventados. As anomalias são plantadas em quantidade conhecida
(ver PLANTADAS) para que os testes confiram que a auditoria e os modelos as
encontram.
"""

import csv
from datetime import datetime, timedelta
from pathlib import Path

from ingest.fontes import FONTES

# O que a auditoria tem de achar na amostra. Os testes usam estes números.
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

CABECALHOS = {
    "customers": [
        "customer_id", "customer_unique_id", "customer_zip_code_prefix",
        "customer_city", "customer_state",
    ],
    "geolocation": [
        "geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng",
        "geolocation_city", "geolocation_state",
    ],
    "orders": [
        "order_id", "customer_id", "order_status", "order_purchase_timestamp",
        "order_approved_at", "order_delivered_carrier_date",
        "order_delivered_customer_date", "order_estimated_delivery_date",
    ],
    "order_items": [
        "order_id", "order_item_id", "product_id", "seller_id",
        "shipping_limit_date", "price", "freight_value",
    ],
    "order_payments": [
        "order_id", "payment_sequential", "payment_type", "payment_installments",
        "payment_value",
    ],
    "order_reviews": [
        "review_id", "order_id", "review_score", "review_comment_title",
        "review_comment_message", "review_creation_date", "review_answer_timestamp",
    ],
    "products": [
        "product_id", "product_category_name", "product_name_lenght",
        "product_description_lenght", "product_photos_qty", "product_weight_g",
        "product_length_cm", "product_height_cm", "product_width_cm",
    ],
    "sellers": ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"],
    "product_category_translation": [
        "product_category_name", "product_category_name_english",
    ],
    "marketing_qualified_leads": ["mql_id", "first_contact_date", "landing_page_id", "origin"],
    "closed_deals": [
        "mql_id", "seller_id", "sdr_id", "sr_id", "won_date", "business_segment",
        "lead_type", "lead_behaviour_profile", "has_company", "has_gtin",
        "average_stock", "business_type", "declared_product_catalog_size",
        "declared_monthly_revenue",
    ],
}  # fmt: skip

TS = "%Y-%m-%d %H:%M:%S"


def _ts(d: datetime | None) -> str:
    return d.strftime(TS) if d else ""


def gerar() -> dict[str, list[list[str]]]:
    """Monta as linhas de cada tabela. Determinístico: sem aleatoriedade."""
    t: dict[str, list[list[str]]] = {nome: [] for nome in CABECALHOS}

    # Categorias e produtos: p5 sem categoria
    t["product_category_translation"] = [
        ["beleza_saude", "health_beauty"],
        ["esporte_lazer", "sports_leisure"],
        ["informatica_acessorios", "computers_accessories"],
    ]
    cats = ["beleza_saude", "esporte_lazer", "informatica_acessorios", "beleza_saude", ""]
    for i, cat in enumerate(cats, 1):
        t["products"].append([f"p{i}", cat, "40", "300", "2", "500", "20", "10", "15"])

    # Lojistas que venderam: s1..s4. s5 e s6 só têm contrato.
    for i in range(1, 5):
        t["sellers"].append([f"s{i}", f"0{i}000", "sao paulo", "SP"])
        t["geolocation"].append([f"0{i}000", "-23.5", "-46.6", "sao paulo", "SP"])

    # Leads: 10, um sem origem e um 'unknown'
    origens = [
        "organic_search", "paid_search", "social", "organic_search", "email",
        "paid_search", "", "unknown", "referral", "direct_traffic",
    ]  # fmt: skip
    # O funil começa antes das vendas: lojista contratado só vende depois do
    # contrato, como no dado real (nenhum caso ao contrário).
    inicio_funil = datetime(2017, 11, 1)
    for i, origem in enumerate(origens, 1):
        contato = (inicio_funil + timedelta(days=7 * i)).date().isoformat()
        t["marketing_qualified_leads"].append([f"m{i:02d}", contato, f"lp{i % 3}", origem])

    # Contratos: m01->s1, m02->s2, m03->s5 e m04->s6 (s5 e s6 nunca vendem)
    for mql, seller, dias in [("m01", "s1", 10), ("m02", "s2", 12), ("m03", "s5", 30),
                              ("m04", "s6", 40)]:  # fmt: skip
        n = int(mql[1:])
        won = inicio_funil + timedelta(days=7 * n + dias, hours=14)
        t["closed_deals"].append([
            mql, seller, "sdr1", "sr1", _ts(won), "health_beauty", "online_medium",
            "cat", "", "", "", "reseller", "", "0.0",
        ])  # fmt: skip

    # Clientes: 30 customer_ids, 26 pessoas (u01..u04 compram duas vezes)
    for i in range(1, 31):
        pessoa = f"u{(i - 1) % 26 + 1:02d}"
        t["customers"].append([f"c{i:02d}", pessoa, "01000", "sao paulo", "SP"])

    # Pedidos: 30. o29 e o30 sem itens (indisponível e cancelado), mas pagos.
    for i in range(1, 31):
        compra = datetime(2018, 1, 1, 10) + timedelta(days=5 * i)
        status = "delivered"
        aprov = compra + timedelta(hours=2)
        carrier = compra + timedelta(days=1)
        entrega = compra + timedelta(days=6)
        if i == 3:  # envio antes da compra
            carrier = compra - timedelta(days=1)
        if i in (27, 28):  # cancelados com itens e pagamento
            status, carrier, entrega = "canceled", None, None
        if i == 29:
            status, carrier, entrega = "unavailable", None, None
        if i == 30:
            status, carrier, entrega = "canceled", None, None
        estimada = (compra + timedelta(days=15)).date().isoformat() + " 00:00:00"
        t["orders"].append([
            f"o{i:02d}", f"c{i:02d}", status, _ts(compra), _ts(aprov), _ts(carrier),
            _ts(entrega), estimada,
        ])  # fmt: skip

        if i >= 29:
            t["order_payments"].append([f"o{i:02d}", "1", "credit_card", "1", "80.00"])
            continue
        valores = []
        for item in range(1, 3 if i % 4 == 0 else 2):
            # o07 (o pedido sem pagamento) é barato, como no dado real, para não
            # distorcer a receita paga de uma amostra de 30 pedidos
            preco, frete = (15, 5) if i == 7 else (200 + i, 10)
            valores.append(preco + frete)
            t["order_items"].append([
                f"o{i:02d}", str(item), f"p{(i + item) % 5 + 1}", f"s{(i + item) % 4 + 1}",
                _ts(compra + timedelta(days=3)), f"{preco:.2f}", f"{frete:.2f}",
            ])  # fmt: skip

        total = sum(valores)
        if i == 7:  # sem pagamento
            pass
        elif i in (5, 10, 15):  # juros de parcelamento
            t["order_payments"].append([f"o{i:02d}", "1", "credit_card", "6",
                                        f"{total * 1.02:.2f}"])  # fmt: skip
        elif i == 12:  # cartão + voucher zerado
            t["order_payments"].append([f"o{i:02d}", "1", "credit_card", "1", f"{total:.2f}"])
            t["order_payments"].append([f"o{i:02d}", "2", "voucher", "1", "0.00"])
        else:
            t["order_payments"].append([f"o{i:02d}", "1", "boleto", "1", f"{total:.2f}"])

        if status == "delivered":
            review = "r01" if i in (1, 2) else f"r{i:02d}"  # r01 aparece em dois pedidos
            criada = (compra + timedelta(days=7)).date().isoformat() + " 00:00:00"
            t["order_reviews"].append([review, f"o{i:02d}", str(i % 5 + 1), "", "",
                                       criada, _ts(compra + timedelta(days=8))])  # fmt: skip
    return t


def escrever(destino: Path) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    tabelas = gerar()
    caminhos = []
    for fonte in FONTES:
        caminho = destino / fonte.arquivo
        with caminho.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(CABECALHOS[fonte.tabela])
            w.writerows(tabelas[fonte.tabela])
        caminhos.append(caminho)
    return caminhos
