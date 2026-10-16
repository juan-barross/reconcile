with primeira_venda as (
    select
        i.seller_id,
        min(o.purchased_at) as em
    from staging.stg_olist__order_items as i
    inner join staging.stg_olist__orders as o on i.order_id = o.order_id
    group by 1
),

contratos as (
    select
        strftime(m.first_contact_date, '%Y-%m') as contato,
        strftime(d.won_at, '%Y-%m') as fechamento,
        strftime(v.em, '%Y-%m') as venda
    from staging.stg_olist__closed_deals as d
    inner join staging.stg_olist__marketing_qualified_leads as m on d.mql_id = m.mql_id
    left join primeira_venda as v on d.seller_id = v.seller_id
)

select
    count(*) filter (where contato = $mes) as marketing,
    count(*) filter (where contato = $mes and fechamento <> $mes) as contato_fechou_em_outro,
    count(*) filter (where fechamento = $mes and contato <> $mes) as fechou_contato_em_outro,
    count(*) filter (where fechamento = $mes) as vendas,
    count(*) filter (where fechamento = $mes and venda is null) as fechou_nunca_vendeu,
    count(*) filter (where fechamento = $mes and venda <> $mes) as fechou_vendeu_depois,
    count(*) filter (where venda = $mes and fechamento <> $mes) as fechou_antes_vendeu_no_mes,
    count(*) filter (where venda = $mes) as operacao
from contratos
