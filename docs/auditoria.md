# Auditoria da camada raw

Gerado por `reconcile auditar` em 2026-10-10. Não edite à mão.

## Linhas por tabela

| tabela | linhas |
|---|---:|
| `closed_deals` | 842 |
| `customers` | 99.441 |
| `geolocation` | 1.000.163 |
| `marketing_qualified_leads` | 8.000 |
| `order_items` | 112.650 |
| `order_payments` | 103.886 |
| `order_reviews` | 99.224 |
| `orders` | 99.441 |
| `product_category_translation` | 71 |
| `products` | 32.951 |
| `sellers` | 3.095 |

## Checagens

| categoria | checagem | resultado | leitura |
|---|---|---:|---|
| chave | pedidos com order_id repetido | 0 | Chave limpa. |
| chave | itens com (pedido, número do item) repetido | 0 | Chave composta limpa. |
| chave | pagamentos com (pedido, sequência) repetido | 0 | Chave composta limpa. |
| chave | linhas de avaliação que repetem um review_id | 814 | A mesma avaliação aparece em mais de um pedido. A chave é (review_id, order_id). |
| chave | leads com mql_id repetido | 0 | Cada lead tem uma linha, logo uma origem só. |
| chave | contratos com mql_id repetido | 0 | Cada lead fecha no máximo um contrato. |
| cliente | customer_id a mais que pessoas (customer_unique_id) | 3.345 | Cada pedido gera um customer_id novo. Contar por customer_id infla clientes. |
| cliente | pessoas com mais de um customer_id | 2.997 | Clientes que voltaram a comprar. Contados uma vez por pedido se a chave for errada. |
| órfão | itens sem pedido | 0 | Integridade ok. |
| órfão | pagamentos sem pedido | 0 | Integridade ok. |
| órfão | pedidos sem nenhum item | 775 | Quase todos cancelados ou indisponíveis. Entram na contagem de pedidos de quem conta pela tabela de pedidos e somem para quem conta por itens. |
| órfão | pedidos sem pagamento | 1 | Pedido sem registro de pagamento: some da receita do financeiro. |
| órfão | contratos sem lead de origem | 0 | Todo contrato veio de um lead do marketing. |
| órfão | contratos cujo lojista nunca vendeu | 462 | Contrato assinado que não virou lojista ativo. Vendas conta, operação não. |
| data | envio à transportadora antes da compra | 166 | Data impossível. Afeta quem conta vendas pela data de envio. |
| data | entrega ao cliente antes do envio à transportadora | 23 | Data impossível. Afeta prazo de entrega, não receita. |
| data | entregues ou enviados sem data de aprovação | 14 | Somem de quem conta pela data de aprovação, apesar de terem sido entregues. |
| data | status 'delivered' sem data de entrega | 8 | Somem de quem conta pela data de entrega. |
| data | cancelados com data de entrega | 6 | Status e datas se contradizem. Quem filtra por data de entrega conta como venda. |
| data | contrato fechado antes do primeiro contato | 1 | Data impossível no funil. |
| data | contratos fechados depois do último pedido da base | 17 | Não tiveram como vender dentro da base. Entram no denominador da ativação e puxam a taxa para baixo se ninguém tratar. |
| funil | leads sem origem (nula) | 60 | Somados a 'unknown' na análise por canal. |
| funil | leads com origem 'unknown' | 1.099 | Canal desconhecido. Não dá para atribuir receita a um canal. |
| pagamento | pagamentos com valor zero | 9 | Vouchers zerados e 'not_defined'. Não mudam a receita, mas contam como pagamento. |
| pagamento | pedidos pagos a mais que itens + frete (> R$ 1) | 232 | Em geral juros de parcelamento. É a diferença entre a receita do financeiro e a do comercial. |
| produto | produtos sem categoria | 610 | Ficam como 'sem categoria' em qualquer corte por categoria. |
