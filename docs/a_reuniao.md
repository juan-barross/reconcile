# A reunião

Gerado por `reconcile reuniao` a partir das consultas em [`departamentos/`](../departamentos/). Não edite os números à mão.

Cada área da Olist respondeu às mesmas três perguntas com a consulta que faria sozinha. As consultas rodam e contam coisas reais. Discordam porque cada área escolheu uma chave, uma data e um filtro sem registrar a escolha.

## A pauta: mar/2018

| pergunta | marketing | vendas | financeiro | operação |
|---|---:|---:|---:|---:|
| lojistas conquistados | 167 | 147 | — | 25 |
| clientes novos | 7.211 | — | — | 6.965 |
| receita | — | R$ 1.155.126,82 | R$ 1.170.383,27 | — |

Um traço quer dizer que a área não responde essa pergunta.

## Lojistas conquistados

Em mar/2018, marketing diz 167, vendas diz 147 e operação diz 25. No acumulado da base, marketing e vendas empatam em 842 e operação fica em 380.

### Em mar/2018

| | lojistas |
|---|---:|
| **marketing** (mês do primeiro contato) | **167** |
| contato em mar/2018, contrato fechado em outro mês | − 85 |
| contrato fechado em mar/2018, contato em outro mês | + 65 |
| **vendas** (mês do fechamento) | **147** |
| fechou em mar/2018 e nunca vendeu | − 73 |
| fechou em mar/2018 e só vendeu num mês seguinte | − 66 |
| fechou antes e fez a primeira venda em mar/2018 | + 17 |
| **operação** (mês da primeira venda) | **25** |

### Na base inteira

| causa | lojistas | quem é afetado |
|---|---:|---|
| primeiro contato e fechamento em meses diferentes | 431 de 842 (51%) | marketing contra vendas, mês a mês |
| contrato assinado, lojista nunca vendeu | 462 (55%) | vendas contra operação |
| ... dos quais fecharam depois do último pedido da base | 17 | operação não tinha como contar |

Marketing e vendas contam os mesmos 842 contratos, só que em meses diferentes: o marketing credita no mês em que o lead chegou e vendas no mês da assinatura. A mediana entre um e outro é de 14 dias, o bastante para jogar metade dos contratos para o mês seguinte.

Operação só conta quem vendeu, e conta no mês da primeira venda. A diferença para vendas no acumulado é inteira de lojistas que assinaram e nunca venderam: 462 de 842.

## Clientes novos

Marketing conta 99.441 clientes e operação conta 96.096. A diferença, 3.345, é toda de clientes que voltaram a comprar: a Olist cria um `customer_id` novo a cada pedido, e o marketing conta essa coluna. São 2.997 pessoas com mais de um pedido. Em mar/2018 a diferença é 7.211 contra 6.965, pelo mesmo motivo.

| causa | clientes |
|---|---:|
| pedidos de quem já tinha comprado antes, contados como cliente novo | 3.345 |

## Receita

Vendas soma preço dos itens mais frete, pela data da compra. Financeiro soma o que foi pago, pela data de aprovação. A ponte abaixo vai de um número ao outro; cada linha é uma causa e a soma fecha no centavo.

### Na base inteira

| | R$ |
|---|---:|
| **vendas** (itens + frete, data da compra) | **R$ 15.843.553,24** |
| pedidos sem data de aprovação | − R$ 1.954,60 |
| pedidos aprovados sem pagamento registrado | − R$ 143,46 |
| pagamentos de pedidos sem item | + R$ 127.416,78 |
| pago acima de itens + frete (em geral juros) | + R$ 3.071,17 |
| pago abaixo de itens + frete | − R$ 200,78 |
| **financeiro** (pagamentos, data de aprovação) | **R$ 15.971.742,35** |

A maior parcela são R$ 127.416,78 pagos em pedidos sem nenhum item, quase todos cancelados ou indisponíveis: o financeiro viu o dinheiro entrar e vendas nunca registrou o item. Os juros do parcelamento somam R$ 3.071,17, pagos acima de itens + frete em 367 pedidos, 318 deles parcelados.

Cancelados e indisponíveis pesam R$ 108.026,21 na conta de vendas e R$ 235.248,04 na do financeiro. Nenhuma das duas consultas olha o status do pedido.

### Em mar/2018

| | R$ |
|---|---:|
| **vendas** (itens + frete, data da compra) | **R$ 1.155.126,82** |
| pagamentos de pedidos sem item | + R$ 3.902,89 |
| pago acima de itens + frete (em geral juros) | + R$ 79,91 |
| pago abaixo de itens + frete | − R$ 0,16 |
| data de aprovação em outro mês | + R$ 11.273,81 |
| **financeiro** (pagamentos, data de aprovação) | **R$ 1.170.383,27** |

Num mês isolado aparece a causa que some no acumulado: a data. Um pedido feito no dia 31 e aprovado no dia 1º é receita de um mês para vendas e do outro para o financeiro.

## A resposta da camada única

As diferenças acima vêm de decisões que ninguém escreveu: qual coluna identifica o cliente, qual data vale e se pedido cancelado entra. O [contrato de métricas](contrato_de_metricas.md) escreve essas decisões e os marts do dbt as aplicam. Em mar/2018, a camada única responde:

| métrica | mar/2018 | regra (ver contrato) |
|---|---:|---|
| lojistas contratados | 147 | data do contrato |
| lojistas ativados | 25 | primeira venda válida, no mês dela |
| clientes novos | 6.931 | pessoa (`customer_unique_id`), primeira compra válida |
| pedidos válidos | 7.168 | sem cancelados, indisponíveis ou pedidos sem item |
| receita bruta | R$ 1.152.656,99 | itens + frete, data da compra |
| receita paga | R$ 1.164.078,78 | pagamentos, data de aprovação (reserva: compra) |
| ticket médio | R$ 160,81 | receita bruta ÷ pedidos válidos |

Cada área mantém o seu recorte, agora com nome próprio. O que o marketing chamava de lojistas conquistados passa a se chamar "contratos por mês do lead".
