select
    i.order_id,
    i.order_item_id,
    i.seller_id,
    i.product_id,
    coalesce(t.category_name_english, p.category_name, 'sem_categoria') as categoria,
    pv.purchased_at,
    pv.eh_valido,
    i.price,
    i.freight_value
from {{ ref('stg_olist__order_items') }} as i
inner join {{ ref('int_pedidos__valores') }} as pv
    on i.order_id = pv.order_id
left join {{ ref('stg_olist__products') }} as p
    on i.product_id = p.product_id
left join {{ ref('stg_olist__product_category_translation') }} as t
    on p.category_name = t.category_name
