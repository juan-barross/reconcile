-- Clientes são pessoas (customer_unique_id), não customer_id.
-- O total de clientes na dim tem que ser o número de pessoas distintas, vindas
-- direto do staging, com pedido válido. Se alguém trocar a chave para
-- customer_id em qualquer camada, a dim passa a contar pedidos e isto quebra.

with dim as (
    select count(*) as n from {{ ref('dim_clientes') }}
    where eh_cliente
),

pessoas as (
    select count(distinct c.customer_unique_id) as n
    from {{ ref('fct_pedidos') }} as p
    inner join {{ ref('stg_olist__orders') }} as o
        on p.order_id = o.order_id
    inner join {{ ref('stg_olist__customers') }} as c
        on o.customer_id = c.customer_id
    where p.eh_valido
)

select
    dim.n as clientes_na_dim,
    pessoas.n as pessoas_com_pedido_valido
from dim
cross join pessoas
where dim.n <> pessoas.n
