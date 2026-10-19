# A reunião

Gerado por `reconcile reuniao` a partir das consultas em [`departamentos/`](../departamentos/). Não edite os números à mão.

Cada área da Olist respondeu às mesmas três perguntas com a consulta que faria sozinha. As consultas rodam e contam coisas reais. Discordam porque cada área escolheu uma chave, uma data e um filtro sem registrar a escolha.

## A pauta: {m}

{pauta}

Um traço quer dizer que a área não responde essa pergunta.

## Lojistas conquistados

Em {m}, marketing diz {loj_marketing}, vendas diz {loj_vendas} e operação diz {loj_operacao}. No acumulado da base, marketing e vendas empatam em {contratos} e operação fica em {venderam}.

### Em {m}

{lojistas_mes}

### Na base inteira

{lojistas_base}

Marketing e vendas contam os mesmos {contratos} contratos, só que em meses diferentes: o marketing credita no mês em que o lead chegou e vendas no mês da assinatura. A mediana entre um e outro é de {mediana} dias, o bastante para jogar metade dos contratos para o mês seguinte.

Operação só conta quem vendeu, e conta no mês da primeira venda. A diferença para vendas no acumulado é inteira de lojistas que assinaram e nunca venderam: {nunca_venderam} de {contratos}.

## Clientes novos

Marketing conta {customer_ids} clientes e operação conta {pessoas}. A diferença, {contados_a_mais}, é toda de clientes que voltaram a comprar: a Olist cria um `customer_id` novo a cada pedido, e o marketing conta essa coluna. São {pessoas_que_voltaram} pessoas com mais de um pedido. Em {m} a diferença é {cli_marketing} contra {cli_operacao}, pelo mesmo motivo.

{clientes}

## Receita

Vendas soma preço dos itens mais frete, pela data da compra. Financeiro soma o que foi pago, pela data de aprovação. A ponte abaixo vai de um número ao outro; cada linha é uma causa e a soma fecha no centavo.

### Na base inteira

{receita}

A maior parcela são {pago_sem_item} pagos em pedidos sem nenhum item, quase todos cancelados ou indisponíveis: o financeiro viu o dinheiro entrar e vendas nunca registrou o item. Os juros do parcelamento somam {pago_a_mais}, pagos acima de itens + frete em {pago_a_mais_pedidos} pedidos, {pago_a_mais_parcelados} deles parcelados.

Cancelados e indisponíveis pesam {cancelados_vendas} na conta de vendas e {cancelados_financeiro} na do financeiro. Nenhuma das duas consultas olha o status do pedido.

### Em {m}

{receita_mes}

Num mês isolado aparece a causa que some no acumulado: a data. Um pedido feito no dia 31 e aprovado no dia 1º é receita de um mês para vendas e do outro para o financeiro.

## A resposta da camada única

As diferenças acima vêm de decisões que ninguém escreveu: qual coluna identifica o cliente, qual data vale e se pedido cancelado entra. O [contrato de métricas](contrato_de_metricas.md) escreve essas decisões e os marts do dbt as aplicam. Em {m}, a camada única responde:

{camada_unica}

Cada área mantém o seu recorte, agora com nome próprio. O que o marketing chamava de lojistas conquistados passa a se chamar "contratos por mês do lead".
