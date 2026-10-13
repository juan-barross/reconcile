"""Quais arquivos baixamos, de onde, e com que nome entram na camada raw."""

import os
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(os.environ.get("RECONCILE_DATA_DIR", "data"))
CSV_DIR = DATA_DIR / "csv"
DB_PATH = DATA_DIR / "olist.duckdb"


@dataclass(frozen=True)
class Caminhos:
    """Onde ficam os CSVs e o banco. A amostra sintética mora em data/amostra."""

    base: Path
    amostra: bool

    @property
    def csv_dir(self) -> Path:
        return self.base / "csv"

    @property
    def db_path(self) -> Path:
        return self.base / "olist.duckdb"


def caminhos(amostra: bool = False) -> Caminhos:
    return Caminhos(DATA_DIR / "amostra" if amostra else DATA_DIR, amostra)


@dataclass(frozen=True)
class Fonte:
    dataset: str  # handle no Kaggle
    arquivo: str  # nome do CSV dentro do dataset
    tabela: str  # nome da tabela em raw


ECOMMERCE = "olistbr/brazilian-ecommerce"
FUNIL = "olistbr/marketing-funnel-olist"

FONTES: tuple[Fonte, ...] = (
    Fonte(ECOMMERCE, "olist_customers_dataset.csv", "customers"),
    Fonte(ECOMMERCE, "olist_geolocation_dataset.csv", "geolocation"),
    Fonte(ECOMMERCE, "olist_orders_dataset.csv", "orders"),
    Fonte(ECOMMERCE, "olist_order_items_dataset.csv", "order_items"),
    Fonte(ECOMMERCE, "olist_order_payments_dataset.csv", "order_payments"),
    Fonte(ECOMMERCE, "olist_order_reviews_dataset.csv", "order_reviews"),
    Fonte(ECOMMERCE, "olist_products_dataset.csv", "products"),
    Fonte(ECOMMERCE, "olist_sellers_dataset.csv", "sellers"),
    Fonte(ECOMMERCE, "product_category_name_translation.csv", "product_category_translation"),
    Fonte(FUNIL, "olist_marketing_qualified_leads_dataset.csv", "marketing_qualified_leads"),
    Fonte(FUNIL, "olist_closed_deals_dataset.csv", "closed_deals"),
)
