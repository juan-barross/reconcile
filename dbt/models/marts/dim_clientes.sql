with pedidos as (
    select * from {{ ref('int_pedidos__valores') }}
),

estado as (
    select
        p.customer_unique_id,
        arg_max(c.state, p.purchased_at) as estado
    from pedidos as p
    inner join {{ ref('stg_olist__customers') }} as c
        on p.customer_id = c.customer_id
    group by 1
)

select
    cast(p.customer_unique_id as varchar) as customer_unique_id,
    cast(e.estado as varchar) as estado,
    cast(count(*) filter (where p.eh_valido) > 0 as boolean) as eh_cliente,
    cast(min(p.purchased_at) filter (where p.eh_valido) as timestamp) as primeira_compra_em,
    cast(count(*) filter (where p.eh_valido) as bigint) as pedidos_validos,
    cast(coalesce(sum(p.valor_itens_frete) filter (where p.eh_valido), 0) as decimal(18, 2))
        as receita_bruta
from pedidos as p
inner join estado as e
    on p.customer_unique_id = e.customer_unique_id
group by 1, 2
