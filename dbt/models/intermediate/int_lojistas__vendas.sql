select
    seller_id,
    min(purchased_at) as primeira_venda_em,
    max(purchased_at) as ultima_venda_em,
    count(distinct order_id) as pedidos_validos,
    sum(price + freight_value) as receita_bruta
from {{ ref('int_itens__enriquecidos') }}
where eh_valido
group by 1
