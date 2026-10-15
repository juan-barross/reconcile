-- Regra de pedido válido do contrato; pedido não válido não carrega receita.

select
    order_id,
    status,
    n_itens,
    eh_valido,
    receita_bruta,
    receita_paga
from {{ ref('fct_pedidos') }}
where
    (eh_valido and (status in ('canceled', 'unavailable') or n_itens = 0))
    or (not eh_valido and status not in ('canceled', 'unavailable') and n_itens > 0)
    or (not eh_valido and (receita_bruta <> 0 or receita_paga <> 0))
