# O dia em que alguém mexeu na origem

Gerado por `reconcile quebrar` em 2026-10-13 sobre o dado real da Olist. Não edite à mão.

Cada cenário abaixo reintroduz, de propósito e numa cópia, uma das causas de divergência da [reunião](a_reuniao.md): pelo dado bruto ou pelo código de um modelo. O `dbt build` roda inteiro e a tabela diz quais testes pegaram a quebra. Um cenário sem nenhum teste falhando seria uma divergência que voltaria calada.

Quando um teste do staging falha, o `dbt build` não constrói os modelos que dependem dele. Por isso a quebra na origem aparece num teste só: os marts, e o painel que lê os marts, nunca chegam a ver o dado duplicado.

| cenário | o que mudou | testes que falharam |
|---|---|---|
| **controle** | Nada. Serve para mostrar que, sem mudança, nenhum teste falha. | nenhum |
| **pagamento duplicado na origem** | O sistema de pagamentos reenviou cerca de 5% dos pagamentos (mesmo pedido, mesma sequência). | `dbt_utils_unique_combination_of_columns_stg_olist__order_payments_order_id__payment_sequential` (5.294 linhas) |
| **cliente duplicado na origem** | O cadastro exportou de novo cerca de 2% dos clientes. | `unique_stg_olist__customers_customer_id` (1.995 linhas) |
| **cliente contado por customer_id** | Alguém trocou a chave de cliente para customer_id no intermediate. | `clientes_contados_por_pessoa` (1 linha) |
| **cancelados de volta** | Alguém tirou o filtro de status da regra de pedido válido. | `pedido_valido_segue_o_contrato` (467 linhas) |
| **regra de data trocada** | Alguém passou a datar a receita paga pela compra, e não pela aprovação. | `regra_de_data_da_receita_paga` (97.985 linhas) |
