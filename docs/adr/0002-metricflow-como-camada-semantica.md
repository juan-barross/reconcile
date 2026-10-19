# ADR 0002: MetricFlow como camada semântica

- **Status:** aceita
- **Data:** 2026-10-10

## Contexto

O problema do projeto é cada área calcular a mesma métrica do seu jeito. Ter os marts certos não basta: se o painel, o agente e a planilha de alguém reescrevem `sum(...)` com filtros diferentes, a divergência volta.

Precisamos de um lugar onde cada métrica (cliente ganho, receita paga, pedido válido etc.) seja definida uma vez, com a regra de data e as exclusões, e que outros consumidores consultem pelo nome.

Opções consideradas:

1. **Views SQL** com uma coluna por métrica.
2. **MetricFlow**, o motor de métricas open source do dbt (`semantic_models` e `metrics` em YAML).
3. **Cube** ou outra camada semântica separada do dbt.

## Decisão

MetricFlow, com as definições em `dbt/models/semantic/` e consulta pelo CLI `mf` (pacote `dbt-metricflow`).

## Por quê

- Fica no mesmo projeto dbt: as métricas são versionadas, testadas e documentadas junto com os modelos que as alimentam.
- Uma métrica declarada com `agg_time_dimension` carrega a regra de data. "Receita paga por mês" sempre usa a data de aprovação, sem ninguém precisar lembrar.
- O agente pode ser restrito a chamar `mf query --metrics ... --group-by ...`. Ele escolhe métricas pelo nome em vez de escrever SQL.
- Views SQL resolvem o caso simples, mas não compõem: cada combinação de métrica, granularidade e filtro vira uma view nova.
- Cube exigiria outro serviço e outra linguagem de definição, e o ganho para este escopo é pequeno.

## Consequências

- `dbt-metricflow` fixa as versões de `dbt-core` que aceita. O `uv.lock` trava a combinação que funciona.
- O painel lê os marts, e um teste compara os marts com `mf query` mês a mês.
