# ADR 0001: DuckDB como armazém, não PostgreSQL

- **Status:** aceita
- **Data:** 2026-10-10

## Contexto

O projeto precisa de um armazém para a camada `raw`, os modelos dbt e as consultas de cada área. As duas opções naturais eram PostgreSQL em Docker, que é o que uma empresa média costuma ter, e DuckDB, um banco analítico que roda num arquivo, sem servidor.

O volume é pequeno: cerca de 1,5 milhão de linhas somando as 11 tabelas, a maior parte em geolocalização. Qualquer uma das duas opções aguenta.

O critério que decide é outro: quem avalia o projeto (um recrutador, um revisor) precisa conseguir reproduzir os números em poucos minutos, de preferência com um comando só.

## Decisão

DuckDB, num arquivo em `data/olist.duckdb`, com o adaptador `dbt-duckdb`.

## Por quê

- **Reprodução com um comando.** `uv sync && uv run reconcile tudo` baixa, carrega, roda o dbt e imprime a reunião. Não precisa de Docker, porta livre nem senha.
- **CI barata.** O GitHub Actions roda `dbt build` sem subir um serviço de banco.
- **MetricFlow suporta DuckDB** de forma oficial (`dbt-metricflow[duckdb]`).
- **O SQL continua portável.** Os modelos usam SQL padrão e as macros do dbt para datas. Mudar para Postgres significa trocar o perfil em `profiles.yml` e ajustar poucas funções.

## Consequências

- O Metabase não fala DuckDB de fábrica. O `docker-compose.yml` monta uma imagem com o driver comunitário da MotherDuck e abre o arquivo **em modo leitura** (ver ADR 0003).
- O DuckDB aceita um processo escrevendo por vez. Rodar `dbt build` com o Metabase aberto pode falhar por trava no arquivo; o README explica a ordem (construir antes, abrir o painel depois).
- Perde-se a demonstração de permissões por papel (`GRANT`), que no Postgres separaria quem lê `raw` de quem lê `marts`. A separação fica por esquema e é verificada nos testes.
