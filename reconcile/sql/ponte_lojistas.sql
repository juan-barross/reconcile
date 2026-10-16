with vendeu as (
    select distinct seller_id from staging.stg_olist__order_items
),

fim_da_base as (
    select max(purchased_at) as fim from staging.stg_olist__orders
)

select
    count(*) as contratos,
    count(*) filter (where v.seller_id is null) as nunca_venderam,
    count(*) filter (where v.seller_id is null and d.won_at > f.fim) as fechados_depois_da_base,
    count(*) filter (where v.seller_id is not null) as venderam,
    count(*) filter (
        where date_trunc('month', m.first_contact_date) <> date_trunc('month', d.won_at)
    ) as fora_do_mes,
    median(datediff('day', m.first_contact_date, d.won_at)) as mediana_dias
from staging.stg_olist__closed_deals as d
inner join staging.stg_olist__marketing_qualified_leads as m on d.mql_id = m.mql_id
left join vendeu as v on d.seller_id = v.seller_id
cross join fim_da_base as f
