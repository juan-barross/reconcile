# ADR 0004: Painel estático no lugar do Metabase

- **Status:** aceita, substitui a [ADR 0003](0003-metabase-como-bi.md)
- **Data:** 2026-10-15

## Contexto

A ADR 0003 escolheu o Metabase em Docker como painel. Na prática, duas coisas pesaram contra:

- A máquina do projeto tem 4 GB de RAM. O Metabase (Java) ocupa perto de 1 GB e o arquivo do DuckDB não pode estar aberto para escrita enquanto o painel lê.
- Quem avalia o projeto teria de subir um contêiner para ver um único gráfico. O painel existia, mas ninguém o veria.

## Decisão

`reconcile painel` gera `docs/painel.md` com gráficos em PNG e a tabela mensal das métricas do contrato, lidos só dos marts. O GitHub mostra a página sem instalar nada.

## Consequências

- A regra da ADR 0003 continua: o painel lê só a camada única.
- Perde-se a exploração interativa. Para perguntas fora do painel, há `reconcile metricas` (camada semântica) e o agente.
- Os arquivos do Docker saíram do repositório.
