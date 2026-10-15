with jornada as (
    select
        sum(receita_bruta_acumulada) as receita,
        count(*) filter (where foi_ativado) as ativados
    from {{ ref('fct_jornada_lojista') }}
),

itens as (
    select
        sum(i.receita_bruta) as receita,
        count(distinct i.seller_id) filter (where i.eh_valido) as ativados
    from {{ ref('fct_itens') }} as i
    inner join {{ ref('fct_jornada_lojista') }} as j
        on i.seller_id = j.seller_id
)

select
    jornada.receita as receita_jornada,
    itens.receita as receita_itens,
    jornada.ativados as ativados_jornada,
    itens.ativados as ativados_itens
from jornada
cross join itens
where
    abs(jornada.receita - itens.receita) > 0.005
    or jornada.ativados <> itens.ativados
