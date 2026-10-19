# O agente contra o painel

Gerado por `reconcile avaliar` com `anthropic/claude-opus-5.5`. Não edite os números à mão.

As mesmas 48 perguntas de negócio foram feitas às duas versões do agente. Uma resposta é consistente quando fica a menos de 0,5% do número da camada única, o mesmo do [painel](painel.md).

| versão | acesso | consistentes | tokens (entrada / saída) | custo |
|---|---|---:|---:|---:|
| A | SQL nas tabelas brutas (raw) | 25 de 48 (52%) | 87.689 / 24.396 | US$ 0,84 |
| B | só as métricas do contrato | 48 de 48 (100%) | 87.860 / 9.991 | US$ 0,55 |

## Por métrica

| métrica | A | B |
|---|---:|---:|
| leads | 6 de 6 | 6 de 6 |
| lojistas_contratados | 6 de 6 | 6 de 6 |
| lojistas_ativados | 0 de 6 | 6 de 6 |
| pedidos_validos | 2 de 6 | 6 de 6 |
| clientes_novos | 3 de 6 | 6 de 6 |
| receita_bruta | 0 de 6 | 6 de 6 |
| receita_paga | 2 de 6 | 6 de 6 |
| ticket_medio | 6 de 6 | 6 de 6 |
