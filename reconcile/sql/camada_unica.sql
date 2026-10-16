with valores as (
    select
        (
            select count(*) from marts.dim_leads
            where strftime(primeiro_contato_em, '%Y-%m') = $mes
        ) as leads,
        (
            select count(*) from marts.fct_jornada_lojista
            where strftime(contratado_em, '%Y-%m') = $mes
        ) as lojistas_contratados,
        (
            select count(*) from marts.fct_jornada_lojista
            where foi_ativado and strftime(primeira_venda_em, '%Y-%m') = $mes
        ) as lojistas_ativados,
        (
            select count(*) from marts.dim_clientes
            where strftime(primeira_compra_em, '%Y-%m') = $mes
        ) as clientes_novos,
        (
            select count(*) from marts.fct_pedidos
            where eh_valido and strftime(comprado_em, '%Y-%m') = $mes
        ) as pedidos_validos,
        (
            select coalesce(sum(receita_bruta), 0) from marts.fct_pedidos
            where strftime(comprado_em, '%Y-%m') = $mes
        ) as receita_bruta,
        (
            select coalesce(sum(receita_paga), 0) from marts.fct_pedidos
            where strftime(receita_paga_em, '%Y-%m') = $mes
        ) as receita_paga
)

select
    *,
    coalesce(receita_bruta / nullif(pedidos_validos, 0), 0) as ticket_medio
from valores
