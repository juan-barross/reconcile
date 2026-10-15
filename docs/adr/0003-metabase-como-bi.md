# ADR 0003: Metabase como BI, lendo só os marts

- **Status:** substituída pela [ADR 0004](0004-painel-estatico-no-lugar-do-metabase.md)
- **Data:** 2026-10-10

## Contexto

O painel é o que a reunião do mês vai olhar. Ele precisa ser uma ferramenta que uma empresa média de fato usa e precisa ler só a camada única. Se o painel tiver acesso a `raw`, alguém acaba montando uma pergunta direto na origem e a divergência volta pela porta dos fundos.

## Decisão

Metabase OSS em Docker, com o driver DuckDB da MotherDuck, abrindo `data/olist.duckdb` em modo leitura. As perguntas do painel usam só tabelas do esquema `marts`.

## Por quê

- O Metabase é gratuito, roda num contêiner e é comum em empresas de tecnologia de porte médio.
- Modo leitura evita que o painel trave ou altere o arquivo do armazém.
- Restringir a `marts` é a regra que dá sentido ao projeto: um número no painel tem que ser o mesmo que o contrato de métricas define.

## Consequências

- O driver DuckDB não vem no Metabase. O `docker/metabase/Dockerfile` baixa o Metabase e o driver em versões fixas.
- O Metabase é opcional para reproduzir os números: tudo que o painel mostra também sai pelo `reconcile` no terminal. Quem só quer conferir os resultados não precisa de Docker.
- A versão do driver precisa ler o formato de arquivo da versão do DuckDB usada no Python. As duas são fixadas juntas e atualizadas juntas.
