with parametro as (
    select cast($mes as varchar) as mes
),

itens as (
    select
        order_id,
        sum(price + freight_value) as vi
    from staging.stg_olist__order_items
    group by 1
),

pagamentos as (
    select
        order_id,
        sum(payment_value) as vp,
        max(payment_installments) as parcelas
    from staging.stg_olist__order_payments
    group by 1
),

base as (
    select
        i.vi,
        pg.vp,
        pg.parcelas,
        o.approved_at is not null as aprovado,
        o.order_status in ('canceled', 'unavailable') as cancelado,
        coalesce(p.mes is null or strftime(o.purchased_at, '%Y-%m') = p.mes, false)
            as comprado_no_periodo,
        coalesce(p.mes is null or strftime(o.approved_at, '%Y-%m') = p.mes, false)
            as aprovado_no_periodo
    from staging.stg_olist__orders as o
    cross join parametro as p
    left join itens as i on o.order_id = i.order_id
    left join pagamentos as pg on o.order_id = pg.order_id
),

compra as (
    select * from base where comprado_no_periodo
)

select
    coalesce(sum(vi), 0) as vendas,
    coalesce(sum(vi) filter (where not aprovado), 0) as sem_aprovacao,
    coalesce(sum(vi) filter (where aprovado and vp is null), 0) as sem_pagamento,
    coalesce(sum(vp) filter (where aprovado and vi is null), 0) as pago_sem_item,
    coalesce(sum(vp - vi) filter (where aprovado and vp > vi), 0) as pago_a_mais,
    count(*) filter (where aprovado and vp > vi) as pago_a_mais_pedidos,
    count(*) filter (where aprovado and vp > vi and parcelas > 1) as pago_a_mais_parcelados,
    coalesce(sum(vp - vi) filter (where aprovado and vp < vi), 0) as pago_a_menos,
    count(*) filter (where aprovado and vp < vi) as pago_a_menos_pedidos,
    coalesce(sum(vp) filter (where aprovado), 0) as financeiro_pela_compra,
    coalesce(sum(vi) filter (where cancelado), 0) as cancelados_vendas,
    coalesce(sum(vp) filter (where aprovado and cancelado), 0) as cancelados_financeiro,
    (
        select coalesce(sum(vp), 0) from base
        where aprovado and aprovado_no_periodo
    ) as financeiro
from compra
