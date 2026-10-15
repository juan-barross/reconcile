-- As janelas de 90 e 180 dias só valem onde observado_* é verdadeiro.

{% set fim = "cast('" ~ var('fim_observacao') ~ "' as date)" %}

with contratos as (
    select * from {{ ref('stg_olist__closed_deals') }}
),

receita_180d as (
    select
        c.seller_id,
        sum(i.price + i.freight_value) as receita_bruta_180d
    from contratos as c
    inner join {{ ref('int_itens__enriquecidos') }} as i
        on c.seller_id = i.seller_id
    where
        i.eh_valido
        and i.purchased_at < c.won_at + interval 180 day
    group by 1
),

jornada as (
    select
        c.mql_id,
        c.seller_id,
        l.canal,
        c.business_segment as segmento,
        c.lead_type as tipo_lead,
        l.first_contact_date as primeiro_contato_em,
        c.won_at as contratado_em,
        v.primeira_venda_em,
        datediff('day', l.first_contact_date, c.won_at) as dias_contato_ate_contrato,
        datediff('day', c.won_at, v.primeira_venda_em) as dias_contrato_ate_primeira_venda,
        greatest(datediff('day', cast(c.won_at as date), {{ fim }}), 0) as dias_observados,
        coalesce(v.pedidos_validos, 0) as pedidos_validos,
        coalesce(v.receita_bruta, 0) as receita_bruta_acumulada,
        coalesce(r.receita_bruta_180d, 0) as receita_bruta_180d
    from contratos as c
    inner join {{ ref('int_leads__canal') }} as l
        on c.mql_id = l.mql_id
    left join {{ ref('int_lojistas__vendas') }} as v
        on c.seller_id = v.seller_id
    left join receita_180d as r
        on c.seller_id = r.seller_id
)

select
    cast(mql_id as varchar) as mql_id,
    cast(seller_id as varchar) as seller_id,
    cast(canal as varchar) as canal,
    cast(segmento as varchar) as segmento,
    cast(tipo_lead as varchar) as tipo_lead,
    cast(primeiro_contato_em as date) as primeiro_contato_em,
    cast(contratado_em as timestamp) as contratado_em,
    cast(primeira_venda_em as timestamp) as primeira_venda_em,
    cast(dias_contato_ate_contrato as integer) as dias_contato_ate_contrato,
    cast(dias_contrato_ate_primeira_venda as integer) as dias_contrato_ate_primeira_venda,
    cast(dias_observados as integer) as dias_observados,
    cast(primeira_venda_em is not null as boolean) as foi_ativado,
    cast(dias_observados >= 90 as boolean) as observado_90d,
    cast(coalesce(dias_contrato_ate_primeira_venda <= 90, false) as boolean) as ativado_em_90d,
    cast(dias_observados >= 180 as boolean) as observado_180d,
    cast(pedidos_validos as bigint) as pedidos_validos,
    cast(receita_bruta_acumulada as decimal(18, 2)) as receita_bruta_acumulada,
    cast(receita_bruta_180d as decimal(18, 2)) as receita_bruta_180d
from jornada
