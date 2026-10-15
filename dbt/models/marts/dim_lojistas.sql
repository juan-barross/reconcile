with ids as (
    select seller_id from {{ ref('stg_olist__sellers') }}
    union
    select seller_id from {{ ref('stg_olist__closed_deals') }}
)

select
    cast(ids.seller_id as varchar) as seller_id,
    cast(d.mql_id is not null as boolean) as tem_contrato,
    cast(d.mql_id as varchar) as mql_id,
    cast(l.canal as varchar) as canal,
    cast(d.business_segment as varchar) as segmento,
    cast(d.lead_type as varchar) as tipo_lead,
    cast(d.won_at as timestamp) as contratado_em,
    cast(v.primeira_venda_em as timestamp) as primeira_venda_em,
    cast(coalesce(v.pedidos_validos, 0) as bigint) as pedidos_validos,
    cast(coalesce(v.receita_bruta, 0) as decimal(18, 2)) as receita_bruta,
    cast(s.state as varchar) as estado,
    cast(s.city as varchar) as cidade
from ids
left join {{ ref('stg_olist__sellers') }} as s
    on ids.seller_id = s.seller_id
left join {{ ref('stg_olist__closed_deals') }} as d
    on ids.seller_id = d.seller_id
left join {{ ref('int_leads__canal') }} as l
    on d.mql_id = l.mql_id
left join {{ ref('int_lojistas__vendas') }} as v
    on ids.seller_id = v.seller_id
