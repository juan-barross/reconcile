select
    cast(l.mql_id as varchar) as mql_id,
    cast(l.first_contact_date as date) as primeiro_contato_em,
    cast(l.canal as varchar) as canal,
    cast(l.landing_page_id as varchar) as landing_page_id,
    cast(d.mql_id is not null as boolean) as virou_contrato,
    cast(d.seller_id as varchar) as seller_id
from {{ ref('int_leads__canal') }} as l
left join {{ ref('stg_olist__closed_deals') }} as d
    on l.mql_id = d.mql_id
