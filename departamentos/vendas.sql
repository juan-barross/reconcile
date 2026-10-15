-- Vendas: lojista conquistado = contrato, no mês do fechamento.
-- Receita = itens + frete no mês da compra, cancelados inclusive.

select
    'vendas' as area,
    'lojistas conquistados' as pergunta,
    strftime(won_at, '%Y-%m') as mes,
    count(*) as valor
from staging.stg_olist__closed_deals
group by 3

union all

select
    'vendas' as area,
    'receita' as pergunta,
    strftime(o.purchased_at, '%Y-%m') as mes,
    sum(i.price + i.freight_value) as valor
from staging.stg_olist__order_items as i
inner join staging.stg_olist__orders as o
    on i.order_id = o.order_id
group by 3
