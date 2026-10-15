select
    'marketing' as area,
    'lojistas conquistados' as pergunta,
    strftime(m.first_contact_date, '%Y-%m') as mes,
    count(*) as valor
from staging.stg_olist__closed_deals as d
inner join staging.stg_olist__marketing_qualified_leads as m
    on d.mql_id = m.mql_id
group by 3

union all

select
    'marketing' as area,
    'clientes novos' as pergunta,
    strftime(o.purchased_at, '%Y-%m') as mes,
    count(distinct o.customer_id) as valor
from staging.stg_olist__orders as o
group by 3
