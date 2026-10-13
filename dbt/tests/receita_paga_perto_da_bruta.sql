-- Em pedidos válidos, receita paga e receita bruta só diferem por juros e
-- arredondamento. Mais de 1% de diferença no total quer dizer que algum
-- pagamento de pedido cancelado, ou pagamento duplicado, entrou na conta.

select
    sum(receita_bruta) as receita_bruta,
    sum(receita_paga) as receita_paga
from {{ ref('fct_pedidos') }}
having abs(sum(receita_paga) - sum(receita_bruta)) > 0.01 * sum(receita_bruta)
