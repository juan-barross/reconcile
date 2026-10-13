# Reconcile

[![CI](https://github.com/juan-barross/Reconcile-/actions/workflows/ci.yml/badge.svg)](https://github.com/juan-barross/Reconcile-/actions/workflows/ci.yml)

**Os números não batem.** Uma fonte única de verdade para o funil de crescimento da Olist: lead, contrato, primeira venda e receita.

Na reunião do mês, marketing, vendas, financeiro e operação trazem números diferentes para a mesma pergunta. Este projeto reproduz essa divergência com os **dados reais** da Olist, mede o tamanho de cada causa e constrói uma camada única de métricas em dbt para que a divergência não volte.

## O resultado em uma tabela

Março de 2018, "quantos lojistas conquistamos?":

| marketing | vendas | operação |
|---:|---:|---:|
| 167 | 147 | 25 |

Nenhum dos três está errado. Marketing conta pela data do primeiro contato, vendas pela data do contrato e operação pela primeira venda. E 55% dos lojistas contratados (462 de 842) nunca venderam. A conta completa, com receita e clientes, está em **[docs/a_reuniao.md](docs/a_reuniao.md)**. Cada diferença tem causa e tamanho, e as pontes fecham no centavo.

## Teste em poucos minutos

Requer Python 3.12 e [uv](https://docs.astral.sh/uv/). Não precisa de conta no Kaggle nem de Docker.

```bash
git clone https://github.com/juan-barross/Reconcile-.git reconcile
cd reconcile
uv sync
```

**Com o dado real** (baixa ~45 MB do Kaggle, sem login):

```bash
uv run reconcile tudo
```

**Sem rede, com a amostra sintética** (30 pedidos com anomalias plantadas):

```bash
uv run reconcile --amostra tudo
```

`reconcile tudo` faz, em ordem: baixa os CSVs, carrega no DuckDB como texto, roda a auditoria, roda `dbt build` (modelos e testes) e gera a página da reunião. Cada passo também roda sozinho:

| comando | o que faz | saída |
|---|---|---|
| `reconcile baixar` | baixa os 11 CSVs da Olist | `data/csv/` |
| `reconcile carregar` | carrega em `raw`, tudo como texto | `data/olist.duckdb` |
| `reconcile auditar` | duplicatas, órfãos, datas impossíveis | [`docs/auditoria.md`](docs/auditoria.md) |
| `reconcile dbt` | `dbt build` de staging, intermediate e marts | testes no terminal |
| `reconcile reuniao --mes 2018-03` | cada área responde e as pontes explicam | [`docs/a_reuniao.md`](docs/a_reuniao.md) |

Com `--amostra`, as saídas vão para `data/amostra/` e não sobrescrevem `docs/`.

Testes Python (rodam sobre a amostra, sem rede):

```bash
uv run pytest
```

### Painel (opcional)

```bash
uv run reconcile tudo
docker compose up -d
```

O Metabase sobe em http://localhost:3000 e lê `data/olist.duckdb` em modo leitura (ver [ADR 0003](docs/adr/0003-metabase-como-bi.md)).

## Como o projeto está organizado

```text
ingest/          download, carga, auditoria, amostra sintética, reunião e o CLI `reconcile`
departamentos/   a consulta "ingênua" de cada área, sem retoque
dbt/             staging -> intermediate -> marts, com testes
docs/            a reunião, a auditoria e as ADRs
tests/           pytest; roda tudo sobre a amostra sintética
```

As camadas do dbt:

- **staging** (`stg_olist__*`): só tipos e nomes, sem join e sem filtro. Os nomes seguem a origem, em inglês.
- **intermediate** e **marts**: regras de negócio do contrato de métricas, com nomes em português (`fct_pedidos`, `dim_lojistas`, `fct_jornada_lojista`).

## O que a auditoria achou

Do relatório completo em [docs/auditoria.md](docs/auditoria.md):

- 99.441 `customer_id` para 96.096 pessoas: cada pedido gera um identificador novo.
- 462 dos 842 lojistas contratados nunca venderam; 17 deles fecharam contrato depois do último pedido da base.
- 775 pedidos sem nenhum item, 99% deles cancelados ou indisponíveis.
- 166 pedidos enviados à transportadora antes da compra.
- 232 pedidos pagos mais de R$ 1 acima de itens + frete, em geral por juros de parcelamento.
- O CSV de categorias vem com BOM no cabeçalho (achado pelo teste que compara a amostra com o dado real).

## Decisões

- [0001: DuckDB como armazém](docs/adr/0001-duckdb-como-armazem.md)
- [0002: MetricFlow como camada semântica](docs/adr/0002-metricflow-como-camada-semantica.md)
- [0003: Metabase como BI, lendo só os marts](docs/adr/0003-metabase-como-bi.md)

## Andamento

- [x] Ingestão, camada raw e auditoria
- [x] Staging com testes
- [x] Amostra sintética e CI
- [x] A reunião: a divergência entre áreas com números
- [ ] Contrato de métricas, intermediate e marts com contratos de modelo
- [ ] Camada semântica (MetricFlow) e painel no Metabase
- [ ] Prova de que os testes barram divergência reintroduzida
- [ ] Valor por lead por canal, com intervalos
- [ ] Agente "pergunte aos dados", avaliado contra o painel

## Trabalho relacionado

[Samir-AISS/olist-ecommerce-data-platform](https://github.com/Samir-AISS/olist-ecommerce-data-platform) (MIT) faz a engenharia de analytics da parte de e-commerce da Olist, com camadas, esquema estrela, dicionário de KPIs e testes de regra de negócio. Serviu de referência para a estrutura de camadas e o tipo de teste. Nenhum código foi copiado.

O que este projeto acrescenta: a conciliação entre áreas com números, o funil de marketing ligado às vendas reais, a camada semântica consumida pelo painel e pelo agente, e a demonstração de que os testes pegam a divergência quando ela volta.

A taxa de 55% de lojistas que nunca venderam já tinha sido apontada em [RHughes33/olistSellerFunnelAnalysis](https://github.com/RHughes33/olistSellerFunnelAnalysis); aqui o número é reproduzido a partir do dado bruto.

## Dados e licença

- [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
- [Marketing Funnel by Olist](https://www.kaggle.com/datasets/olistbr/marketing-funnel-olist)

Os dados são CC BY-NC-SA 4.0 e não estão no repositório: `reconcile baixar` busca direto do Kaggle. O código é MIT.
