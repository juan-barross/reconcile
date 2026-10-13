-- Receita bruta somada por item e por pedido tem que dar o mesmo número.
-- Se um join multiplicar linhas em qualquer um dos dois fatos, isto quebra.

with por_item as (
    select sum(receita_bruta) as total from {{ ref('fct_itens') }}
),

por_pedido as (
    select sum(receita_bruta) as total from {{ ref('fct_pedidos') }}
)

select
    por_item.total as receita_por_item,
    por_pedido.total as receita_por_pedido
from por_item
cross join por_pedido
where abs(por_item.total - por_pedido.total) > 0.005
