with itens as (
    select
        order_id,
        count(*) as n_itens,
        sum(price) as valor_itens,
        sum(freight_value) as valor_frete
    from {{ ref('stg_olist__order_items') }}
    group by 1
),

pagamentos as (
    select
        order_id,
        count(*) as n_pagamentos,
        sum(payment_value) as valor_pago,
        max(payment_installments) as max_parcelas
    from {{ ref('stg_olist__order_payments') }}
    group by 1
)

select
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    o.order_status,
    o.purchased_at,
    o.approved_at,
    o.delivered_to_customer_at,
    coalesce(o.approved_at, o.purchased_at) as receita_paga_em,
    coalesce(i.n_itens, 0) as n_itens,
    coalesce(i.valor_itens, 0) as valor_itens,
    coalesce(i.valor_frete, 0) as valor_frete,
    coalesce(i.valor_itens, 0) + coalesce(i.valor_frete, 0) as valor_itens_frete,
    coalesce(p.n_pagamentos, 0) as n_pagamentos,
    coalesce(p.valor_pago, 0) as valor_pago,
    p.max_parcelas,
    (
        o.order_status not in ('canceled', 'unavailable')
        and coalesce(i.n_itens, 0) > 0
    ) as eh_valido
from {{ ref('stg_olist__orders') }} as o
inner join {{ ref('stg_olist__customers') }} as c
    on o.customer_id = c.customer_id
left join itens as i
    on o.order_id = i.order_id
left join pagamentos as p
    on o.order_id = p.order_id
