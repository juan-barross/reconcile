with j as (
    select
        canal,
        dias_contrato_ate_primeira_venda,
        dias_observados,
        coalesce(
            foi_ativado and dias_contrato_ate_primeira_venda <= dias_observados, false
        ) as vendeu
    from marts.fct_jornada_lojista
)

select
    canal,
    vendeu,
    case when vendeu then dias_contrato_ate_primeira_venda else dias_observados end as dias
from j
