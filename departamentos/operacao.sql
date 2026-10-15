-- Operação: lojista conquistado = contratado com primeira venda, no mês dela.
-- Cliente novo = pessoa (customer_unique_id) no mês da primeira compra.

with primeira_venda as (
    select
        i.seller_id,
        min(o.purchased_at) as primeira_venda_em
    from staging.stg_olist__order_items as i
    inner join staging.stg_olist__orders as o
        on i.order_id = o.order_id
    group by 1
),

primeira_compra as (
    select
        c.customer_unique_id,
        min(o.purchased_at) as primeira_compra_em
    from staging.stg_olist__orders as o
    inner join staging.stg_olist__customers as c
        on o.customer_id = c.customer_id
    group by 1
)

select
    'operacao' as area,
    'lojistas conquistados' as pergunta,
    strftime(v.primeira_venda_em, '%Y-%m') as mes,
    count(*) as valor
from staging.stg_olist__closed_deals as d
inner join primeira_venda as v
    on d.seller_id = v.seller_id
group by 3

union all

select
    'operacao' as area,
    'clientes novos' as pergunta,
    strftime(primeira_compra_em, '%Y-%m') as mes,
    count(*) as valor
from primeira_compra
group by 3
