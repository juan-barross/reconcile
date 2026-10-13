-- Clientes são pessoas (customer_unique_id), não customer_id.
-- O total de clientes tem que ser o número de pessoas distintas com pedido
-- válido; se alguém trocar a chave para customer_id, o total sobe e isto quebra.

with dim as (
    select count(*) as n from {{ ref('dim_clientes') }} where eh_cliente
),

fato as (
    select count(distinct customer_unique_id) as n
    from {{ ref('fct_pedidos') }}
    where eh_valido
)

select dim.n as clientes_na_dim, fato.n as pessoas_com_pedido_valido
from dim
cross join fato
where dim.n <> fato.n
