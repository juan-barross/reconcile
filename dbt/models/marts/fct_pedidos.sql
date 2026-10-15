-- receita_bruta e receita_paga valem zero em pedido não válido: somar a coluna
-- já dá o número do contrato, sem filtro.

select
    cast(order_id as varchar) as order_id,
    cast(customer_unique_id as varchar) as customer_unique_id,
    cast(order_status as varchar) as status,
    cast(eh_valido as boolean) as eh_valido,
    cast(purchased_at as timestamp) as comprado_em,
    cast(approved_at as timestamp) as aprovado_em,
    cast(receita_paga_em as timestamp) as receita_paga_em,
    cast(n_itens as integer) as n_itens,
    cast(max_parcelas as integer) as max_parcelas,
    cast(valor_itens_frete as decimal(18, 2)) as valor_itens_frete,
    cast(valor_pago as decimal(18, 2)) as valor_pago,
    cast(case when eh_valido then valor_itens_frete else 0 end as decimal(18, 2))
        as receita_bruta,
    cast(case when eh_valido then valor_pago else 0 end as decimal(18, 2))
        as receita_paga
from {{ ref('int_pedidos__valores') }}
