-- A receita paga é datada pela aprovação do pagamento, com a compra como
-- reserva quando a aprovação é nula (contrato de métricas). Se alguém trocar
-- a regra de data no modelo, os meses mudam em silêncio; este teste não deixa.

select
    order_id,
    comprado_em,
    aprovado_em,
    receita_paga_em
from {{ ref('fct_pedidos') }}
where receita_paga_em <> coalesce(aprovado_em, comprado_em)
