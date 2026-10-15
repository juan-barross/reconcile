select
    order_id,
    comprado_em,
    aprovado_em,
    receita_paga_em
from {{ ref('fct_pedidos') }}
where receita_paga_em <> coalesce(aprovado_em, comprado_em)
