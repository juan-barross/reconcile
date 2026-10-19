# Contrato de métricas

Uma definição por métrica, com dono, regra de data e exclusões. A [reunião](a_reuniao.md) mostrou que as áreas discordam porque ninguém escreveu essas escolhas; este documento as escreve. Cada métrica abaixo tem uma coluna num mart e pelo menos um teste no dbt. O teste `tests/test_contrato.py` falha se alguma métrica daqui ficar sem os dois.

Para mudar uma definição, abra um PR que altere este documento e o modelo juntos, com aprovação do dono da métrica. Uma mudança só no SQL traria a divergência de volta.

## Resumo

| id | métrica | dono | regra de data | mart |
|---|---|---|---|---|
| `leads` | Leads qualificados | marketing | primeiro contato | `dim_leads` |
| `lojistas_contratados` | Lojistas contratados (cliente ganho) | vendas | fechamento do contrato | `fct_jornada_lojista` |
| `lojistas_ativados` | Lojistas ativados | operação | primeira venda válida | `fct_jornada_lojista` |
| `pedidos_validos` | Pedidos válidos | operação | compra | `fct_pedidos` |
| `clientes_novos` | Clientes compradores novos | marketing | primeira compra válida | `dim_clientes` |
| `receita_bruta` | Receita bruta (GMV) | vendas | compra | `fct_pedidos`, `fct_itens` |
| `receita_paga` | Receita paga | financeiro | aprovação (reserva: compra) | `fct_pedidos` |
| `ticket_medio` | Ticket médio | vendas | compra | `fct_pedidos` |

## Termos usados em todas as métricas

- **Pedido válido:** status diferente de `canceled` e `unavailable`, e com pelo menos um item. Na base são 8 pedidos com status válido e nenhum item; eles ficam de fora porque não há o que entregar nem como atribuir a um lojista.
- **Pessoa:** `customer_unique_id`. O `customer_id` muda a cada pedido e nunca é usado para contar clientes.
- **Canal:** `origin` do lead. Nulo vira `unknown`.
- **Mês:** mês-calendário, na data do próprio registro. A base não traz fuso horário; as datas são tratadas como horário local de Brasília, sem conversão.
- **Fim da observação:** 31/08/2018. Depois disso a base tem 20 pedidos (contra 6.512 em agosto), então qualquer janela que passe dessa data está incompleta. Fica na variável `fim_observacao` do dbt.

## Métricas

### `leads`: Leads qualificados

- **Fórmula:** contagem de `mql_id`.
- **Data:** `first_contact_date`.
- **Exclusões:** nenhuma.
- **Por que essa data:** é quando a campanha trouxe o lead, e é a data que permite comparar canais.

### `lojistas_contratados`: Lojistas contratados

- **Fórmula:** contagem de contratos fechados (`closed_deals`). Um contrato por lead, um lojista por contrato.
- **Data:** `won_date`, a data de fechamento.
- **Exclusões:** nenhuma.
- **O que mudou em relação à reunião:** o marketing contava esses mesmos contratos no mês do primeiro contato. O número de lojistas contratados num mês é sempre pela data de fechamento. Para saber quantos contratos um mês de leads gerou, a métrica é outra (conversão por coorte de lead) e usa a jornada.

### `lojistas_ativados`: Lojistas ativados

- **Fórmula:** lojistas contratados com pelo menos um pedido válido.
- **Data:** compra do primeiro pedido válido do lojista.
- **Exclusões:** pedidos cancelados ou indisponíveis não ativam. Um lojista da base teve só pedidos cancelados: a operação o contava como ativo, este contrato não conta.
- **Taxa de ativação:** ativados ÷ contratados, sempre com a janela explícita (por exemplo, "em até 90 dias do contrato") e só sobre contratos com a janela inteira observada antes de `fim_observacao`.

### `pedidos_validos`: Pedidos válidos

- **Fórmula:** contagem de pedidos válidos (ver termos).
- **Data:** `order_purchase_timestamp`.
- **Exclusões:** `canceled`, `unavailable` e pedidos sem item.

### `clientes_novos`: Clientes compradores novos

- **Fórmula:** pessoas (`customer_unique_id`) cujo primeiro pedido válido cai no período.
- **Data:** compra do primeiro pedido válido da pessoa.
- **Exclusões:** pedidos não válidos não fazem de ninguém cliente.

### `receita_bruta`: Receita bruta (GMV)

- **Fórmula:** soma de `price + freight_value` dos itens de pedidos válidos.
- **Data:** compra.
- **Exclusões:** pedidos não válidos.
- **Inclui frete:** sim. É o que o comprador pagou pelo pedido antes de juros.

### `receita_paga`: Receita paga

- **Fórmula:** soma de `payment_value` de pedidos válidos, com juros de parcelamento e vouchers.
- **Data:** aprovação do pagamento. Quando a aprovação é nula num pedido válido (19 casos, entregues ou a caminho), usa a data da compra.
- **Exclusões:** pedidos não válidos, inclusive os que tiveram pagamento aprovado.
- **Relação com a receita bruta:** a diferença entre as duas é juros e pequenos arredondamentos, e é testada: não pode passar de 1% da receita bruta no total.

### `ticket_medio`: Ticket médio

- **Fórmula:** `receita_bruta ÷ pedidos_validos`.
- **Data:** compra.
- **Exclusões:** as das duas métricas da fórmula.

## O que fica fora deste contrato

- **Receita da Olist** (comissão sobre a venda). A base não traz a taxa; ela aparece só na análise de valor por lead, como premissa explícita.
- **Cliente ativo** (quem comprou nos últimos N dias). Na base, 97% das pessoas compraram uma vez só, então a métrica teria pouco uso aqui.
