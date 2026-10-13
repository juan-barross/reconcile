# Reconcile

[![CI](https://github.com/juan-barross/Reconcile-/actions/workflows/ci.yml/badge.svg)](https://github.com/juan-barross/Reconcile-/actions/workflows/ci.yml)

**Os números não batem.** Uma fonte única de verdade para o funil de crescimento da Olist: lead, contrato, primeira venda e receita.

Na reunião do mês, marketing, vendas, financeiro e operação trazem números diferentes para a mesma pergunta. Este projeto reproduz essa divergência com os **dados reais** da Olist, mede o tamanho de cada causa, constrói uma camada única de métricas em dbt e MetricFlow, e prova que os testes barram a divergência quando ela volta.

## O resultado

Março de 2018, "quantos lojistas conquistamos?":

| marketing | vendas | operação | camada única |
|---:|---:|---:|---:|
| 167 | 147 | 25 | 147 contratados, 25 ativados |

Nenhuma área está errada. Marketing conta pela data do primeiro contato, vendas pela data do contrato e operação pela primeira venda. A camada única dá nome a cada número e escreve a regra de data num [contrato de métricas](docs/contrato_de_metricas.md). A conta completa, com receita e clientes, está em **[docs/a_reuniao.md](docs/a_reuniao.md)**: cada diferença tem causa e tamanho, e as pontes fecham no centavo.

Com os números confiáveis, a pergunta de negócio ([Growth Review](docs/growth_review.md)):

- **O canal decide quantos leads viram contrato, não quanto cada contrato vende.** A receita por contrato nos primeiros 180 dias não difere entre canais além do ruído. Busca converte 12% dos leads, social 5,7% e e-mail 3,7%, com intervalos de confiança que não se cruzam.
- **O maior vazamento é depois do contrato:** 47% dos lojistas contratados não vendem nada em 180 dias.
- **23% dos contratos não têm canal registrado**, e é o grupo que mais converte.

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

`reconcile tudo` baixa os CSVs, carrega no DuckDB como texto, roda a auditoria, roda `dbt build` (modelos e testes), gera a reunião e o Growth Review. Cada passo também roda sozinho:

| comando | o que faz | saída |
|---|---|---|
| `reconcile baixar` | baixa os 11 CSVs da Olist | `data/csv/` |
| `reconcile carregar` | carrega em `raw`, tudo como texto | `data/olist.duckdb` |
| `reconcile auditar` | duplicatas, órfãos, datas impossíveis | [`docs/auditoria.md`](docs/auditoria.md) |
| `reconcile dbt` | `dbt build` de staging, intermediate e marts | testes no terminal |
| `reconcile reuniao --mes 2018-03` | cada área responde e as pontes explicam | [`docs/a_reuniao.md`](docs/a_reuniao.md) |
| `reconcile metricas --mes 2018-03` | as oito métricas do contrato pela camada semântica | tabela no terminal |
| `reconcile quebrar` | quebra o dado de propósito e mostra o teste que pega | [`docs/o_dia_que_mexeram_na_origem.md`](docs/o_dia_que_mexeram_na_origem.md) |
| `reconcile crescimento` | valor por lead e ativação por canal | [`docs/growth_review.md`](docs/growth_review.md) |

Com `--amostra`, as saídas vão para `data/amostra/` e não sobrescrevem `docs/`.

Testes Python (rodam sobre a amostra, sem rede):

```bash
uv run pytest
```

## O dia em que alguém mexeu na origem

Cada causa de divergência da reunião foi reintroduzida de propósito, numa cópia do banco e do projeto, pelo dado bruto ou pelo código de um modelo. O `dbt build` rodou inteiro em cada cenário, sobre o dado real:

| cenário | teste que pegou |
|---|---|
| nada mudou (controle) | nenhum falha |
| pagamentos reenviados pela origem | chave única de pagamento no staging |
| clientes exportados duas vezes | chave única de cliente no staging |
| chave de cliente trocada para `customer_id` | `clientes_contados_por_pessoa` |
| filtro de cancelados removido | `pedido_valido_segue_o_contrato` |
| receita paga datada pela compra | `regra_de_data_da_receita_paga` |

Detalhes, com o número de linhas que cada teste devolveu, em [docs/o_dia_que_mexeram_na_origem.md](docs/o_dia_que_mexeram_na_origem.md).

## Como o projeto está organizado

```text
ingest/          download, carga, auditoria, amostra sintética, reunião, quebras e o CLI
departamentos/   a consulta "ingênua" de cada área, sem retoque
dbt/             staging -> intermediate -> marts -> semantic, com testes
analysis/        valor por lead, ativação e o Growth Review
docs/            reunião, contrato de métricas, auditoria, quebras, Growth Review e ADRs
tests/           pytest; roda tudo sobre a amostra sintética
```

As camadas do dbt:

- **staging** (`stg_olist__*`): só tipos e nomes, sem join e sem filtro. Os nomes seguem a origem, em inglês.
- **intermediate** e **marts**: regras do [contrato de métricas](docs/contrato_de_metricas.md), com nomes em português (`fct_pedidos`, `dim_clientes`, `fct_jornada_lojista`). Todo mart tem contrato de modelo enforced: coluna a mais, a menos ou de outro tipo para o build.
- **semantic**: as oito métricas do contrato no MetricFlow, cada uma com a sua regra de data. `mf query` devolve os mesmos números dos marts, e um teste confere isso mês a mês.

## O que a auditoria achou

Do relatório completo em [docs/auditoria.md](docs/auditoria.md):

- 99.441 `customer_id` para 96.096 pessoas: cada pedido gera um identificador novo.
- 462 dos 842 lojistas contratados nunca venderam; 17 deles fecharam contrato depois do último pedido da base.
- 775 pedidos sem nenhum item, 99% deles cancelados ou indisponíveis.
- 166 pedidos enviados à transportadora antes da compra.
- 232 pedidos pagos mais de R$ 1 acima de itens + frete, em geral por juros de parcelamento.

## O que deu errado no caminho

- **Um teste que não testava.** A primeira versão de `clientes_contados_por_pessoa` comparava a dimensão de clientes com o fato de pedidos. Se alguém trocasse a chave no intermediate, os dois mudavam juntos e o teste continuava verde. Só apareceu quando a quebra de propósito passou calada; agora o teste compara com as pessoas do staging.
- **A amostra sintética escondia a quebra.** Mesmo com o teste corrigido, a troca de chave passava na amostra: os clientes que compravam duas vezes só tinham pedidos cancelados, então nada mudava. A amostra passou a ter recompra em pedido válido.
- **A amostra também era irreal em outros pontos.** Os testes dos marts pegaram lojistas vendendo antes de assinar contrato (no dado real não há nenhum caso) e juros que pesavam mais de 1% da receita. Os modelos estavam certos; a amostra foi ajustada.
- **Janela de 12 meses impossível.** A jornada nasceu com receita em 12 meses, mas nenhum contrato tem 12 meses observados: o mais antigo é de dez/2017 e a base termina em ago/2018. A janela virou 180 dias.
- **O dbt segurava o arquivo.** Rodar o dbt dentro do mesmo processo Python deixava a conexão do DuckDB aberta e a leitura seguinte falhava. O CLI passou a rodar o dbt em subprocesso.
- **A primeira CI no GitHub falhou** por uma regra de estilo SQL (`group by` misturando nome e posição) que eu não tinha rodado localmente nos marts novos.
- **BOM no CSV.** O CSV de categorias da Olist começa com BOM; o teste que compara a amostra com o dado real achou.

## Decisões

- [0001: DuckDB como armazém](docs/adr/0001-duckdb-como-armazem.md)
- [0002: MetricFlow como camada semântica](docs/adr/0002-metricflow-como-camada-semantica.md)
- [0003: Metabase como BI, lendo só os marts](docs/adr/0003-metabase-como-bi.md)

## Andamento

- [x] Ingestão, camada raw e auditoria
- [x] Staging com testes, amostra sintética e CI
- [x] A reunião: a divergência entre áreas com números
- [x] Contrato de métricas, intermediate e marts com contratos de modelo
- [x] Camada semântica (MetricFlow) batendo com os marts
- [x] Prova de que os testes barram divergência reintroduzida
- [x] Valor por lead por canal, com intervalos, e Growth Review
- [ ] Painel no Metabase (o `docker-compose.yml` sobe o Metabase; as perguntas do painel ainda não estão montadas)
- [ ] Agente "pergunte aos dados", avaliado contra a camada semântica

## Trabalho relacionado

[Samir-AISS/olist-ecommerce-data-platform](https://github.com/Samir-AISS/olist-ecommerce-data-platform) (MIT) faz a engenharia de analytics da parte de e-commerce da Olist, com camadas, esquema estrela, dicionário de KPIs e testes de regra de negócio. Serviu de referência para a estrutura de camadas e o tipo de teste. Nenhum código foi copiado.

O que este projeto acrescenta: a conciliação entre áreas com números, o funil de marketing ligado às vendas reais, a camada semântica, e a demonstração de que os testes pegam a divergência quando ela volta.

A taxa de 55% de lojistas que nunca venderam já tinha sido apontada em [RHughes33/olistSellerFunnelAnalysis](https://github.com/RHughes33/olistSellerFunnelAnalysis); aqui o número é reproduzido a partir do dado bruto.

## Dados e licença

- [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
- [Marketing Funnel by Olist](https://www.kaggle.com/datasets/olistbr/marketing-funnel-olist)

Os dados são CC BY-NC-SA 4.0 e não estão no repositório: `reconcile baixar` busca direto do Kaggle. O código é MIT.
