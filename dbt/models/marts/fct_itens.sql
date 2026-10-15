select
    cast(order_id as varchar) as order_id,
    cast(order_item_id as integer) as order_item_id,
    cast(seller_id as varchar) as seller_id,
    cast(product_id as varchar) as product_id,
    cast(categoria as varchar) as categoria,
    cast(eh_valido as boolean) as eh_valido,
    cast(purchased_at as timestamp) as comprado_em,
    cast(price as decimal(18, 2)) as preco,
    cast(freight_value as decimal(18, 2)) as frete,
    cast(case when eh_valido then price + freight_value else 0 end as decimal(18, 2))
        as receita_bruta
from {{ ref('int_itens__enriquecidos') }}
