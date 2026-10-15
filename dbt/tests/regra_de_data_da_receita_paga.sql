-- Receita paga datada pela aprovação, com a compra como reserva.

select
    order_id,
    comprado_em,
    aprovado_em,
    receita_paga_em
from {{ ref('fct_pedidos') }}
where receita_paga_em <> coalesce(aprovado_em, comprado_em)
