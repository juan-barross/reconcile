select
    sum(receita_bruta) as receita_bruta,
    sum(receita_paga) as receita_paga
from {{ ref('fct_pedidos') }}
having abs(sum(receita_paga) - sum(receita_bruta)) > 0.01 * sum(receita_bruta)
