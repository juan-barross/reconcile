# Reconcile

[![CI](https://github.com/juan-barross/Reconcile-/actions/workflows/ci.yml/badge.svg)](https://github.com/juan-barross/Reconcile-/actions/workflows/ci.yml)

**Os números não batem.** Marketing, vendas, financeiro e operação da Olist respondem à mesma pergunta com números diferentes. Este projeto reproduz a divergência com os **dados reais** da Olist, mede cada causa, constrói uma camada única de métricas em dbt e MetricFlow e prova que os testes barram a divergência quando ela volta.

## Veja o resultado sem instalar nada

| página | o que mostra |
|---|---|
| [A reunião](docs/a_reuniao.md) | cada área responde à mesma pergunta; cada diferença tem causa e tamanho, e as pontes fecham no centavo |
| [O painel](docs/painel.md) | as oito métricas oficiais mês a mês, ao lado do que cada área responderia sozinha |
| [O dia em que alguém mexeu na origem](docs/o_dia_que_mexeram_na_origem.md) | cinco divergências reintroduzidas de propósito e o teste que pegou cada uma |
| [Growth Review](docs/growth_review.md) | quanto vale um lead de cada canal, com intervalos, e três recomendações |
| [Contrato de métricas](docs/contrato_de_metricas.md) | definição, dono, regra de data e exclusões de cada métrica |
| [Auditoria](docs/auditoria.md) | o que a origem tem de estranho antes de qualquer modelo |

## O resultado em uma tabela

Março de 2018, "quantos lojistas conquistamos?":

| marketing | vendas | operação | camada única |
|---:|---:|---:|---:|
| 167 | 147 | 25 | 147 contratados, 25 ativados |

Nenhuma área está errada: marketing conta pela data do primeiro contato, vendas pela data do contrato e operação pela primeira venda. A camada única dá nome a cada número e escreve a regra de data no contrato de métricas.

Com os números confiáveis, a pergunta de negócio:

- **O canal decide quantos leads viram contrato, não quanto cada contrato vende.** Busca converte 12% dos leads, social 5,7% e e-mail 3,7%, com intervalos que não se cruzam; a receita por contrato em 180 dias é a mesma entre canais dentro do ruído.
- **O maior vazamento é depois do contrato:** 47% dos lojistas contratados não vendem nada em 180 dias.
- **23% dos contratos não têm canal registrado**, e é o grupo que mais converte.

## Rode você mesmo

Requer Python 3.12 e [uv](https://docs.astral.sh/uv/). Não precisa de conta no Kaggle nem de Docker.

```bash
git clone https://github.com/juan-barross/Reconcile-.git reconcile
cd reconcile
uv sync
```

Sem rede, com a amostra sintética (30 pedidos com anomalias plantadas, cerca de 2 minutos):

```bash
uv run reconcile --amostra tudo
```

Com o dado real da Olist (baixa ~45 MB do Kaggle, sem login):

```bash
uv run reconcile tudo
```

Testes:

```bash
uv run pytest
```

| comando | o que faz |
|---|---|
| `reconcile baixar` / `carregar` | baixa os 11 CSVs e carrega no esquema `raw` do DuckDB, como texto |
| `reconcile auditar` | checa chaves, órfãos e datas da origem |
| `reconcile dbt` | `dbt build`: modelos, testes e contratos de modelo |
| `reconcile reuniao --mes 2018-03` | a resposta de cada área e as pontes entre elas |
| `reconcile painel` | as métricas do contrato mês a mês, com gráficos |
| `reconcile metricas --mes 2018-03` | as mesmas métricas pela camada semântica (`mf query`) |
| `reconcile quebrar` | reintroduz cada divergência numa cópia e mostra o teste que a pega |
| `reconcile crescimento` | valor por lead e ativação por canal |
| `reconcile perguntar "..." --versao B` | pergunta ao agente |
| `reconcile avaliar` | compara as versões A e B do agente com o painel |

Com `--amostra`, as saídas vão para `data/amostra/` e não sobrescrevem `docs/`.

## O agente "pergunte aos dados"

Duas versões, o mesmo modelo e as mesmas 48 perguntas de negócio ([avaliacao/perguntas.jsonl](avaliacao/perguntas.jsonl)), com a resposta esperada tirada da camada única:

- **A** só tem uma ferramenta de SQL nas tabelas brutas e precisa inventar a definição de cada métrica;
- **B** só enxerga as métricas do contrato.

O código e a avaliação estão prontos e testados com um cliente falso. A rodada contra a API ainda não foi feita; com uma chave em `ANTHROPIC_API_KEY`, `uv run reconcile avaliar` gera `docs/agente.md` com a taxa de consistência e o custo de cada versão. O modelo padrão é `claude-opus-5-5` e pode ser trocado em `RECONCILE_MODELO`.

## Como funciona

```text
CSVs da Olist -> raw (texto) -> staging (tipos) -> intermediate -> marts (contrato) -> MetricFlow
                     |                                                  |
                 auditoria                                  painel, reunião, agente B
```

- **staging** (`stg_olist__*`): só tipos e nomes, sem join e sem filtro.
- **intermediate** e **marts**: as regras do contrato de métricas. Todo mart tem contrato de modelo enforced.
- **semantic**: as oito métricas no MetricFlow, cada uma com a sua regra de data; um teste confere que `mf query` bate com os marts mês a mês.
- **`departamentos/`**: a consulta que cada área faria sozinha, sem retoque.
- **`reconcile/`**: o pacote Python. A lógica fica nos módulos; as consultas, em `reconcile/sql/`; o texto de cada relatório, em `reconcile/modelos/`; as checagens da auditoria e os cenários de quebra, em YAML.

## O que deu errado no caminho

- **Um teste que não testava.** A primeira versão de `clientes_contados_por_pessoa` comparava a dimensão de clientes com o fato de pedidos. Se alguém trocasse a chave no intermediate, os dois mudavam juntos e o teste continuava verde. Só apareceu quando a quebra de propósito passou calada; agora o teste compara com as pessoas do staging.
- **A amostra sintética escondia a quebra.** Os clientes que compravam duas vezes só tinham pedidos cancelados, então trocar a chave não mudava nada. A amostra passou a ter recompra em pedido válido.
- **A amostra também era irreal em outros pontos.** Os testes dos marts pegaram lojistas vendendo antes de assinar contrato (no dado real não há nenhum caso) e juros que pesavam mais de 1% da receita.
- **Janela de 12 meses impossível.** Nenhum contrato tem 12 meses observados: o mais antigo é de dez/2017 e a base termina em ago/2018. A janela virou 180 dias.
- **O dbt segurava o arquivo.** Rodar o dbt no mesmo processo Python deixava a conexão do DuckDB aberta; o dbt passou a rodar em subprocesso.
- **A CI falhou duas vezes no GitHub e passava na minha máquina:** uma regra de estilo SQL que eu não tinha rodado, e o `reconcile quebrar` copiando o projeto dbt antes de instalar os pacotes. Reproduzi a segunda escondendo `dbt_packages`.
- **O painel no Metabase ninguém veria.** Com 4 GB de RAM e um contêiner para subir, virou um painel estático que abre no GitHub ([ADR 0004](docs/adr/0004-painel-estatico-no-lugar-do-metabase.md)).

## Decisões

- [0001: DuckDB como armazém](docs/adr/0001-duckdb-como-armazem.md)
- [0002: MetricFlow como camada semântica](docs/adr/0002-metricflow-como-camada-semantica.md)
- [0003: Metabase como BI](docs/adr/0003-metabase-como-bi.md) (substituída)
- [0004: Painel estático no lugar do Metabase](docs/adr/0004-painel-estatico-no-lugar-do-metabase.md)

## Trabalho relacionado

[Samir-AISS/olist-ecommerce-data-platform](https://github.com/Samir-AISS/olist-ecommerce-data-platform) (MIT) faz a engenharia de analytics da parte de e-commerce da Olist e serviu de referência para a estrutura de camadas e o tipo de teste. Nenhum código foi copiado. Este projeto acrescenta a conciliação entre áreas, o funil de marketing ligado às vendas, a camada semântica, a prova de que os testes pegam a divergência e o agente.

A taxa de 55% de lojistas que nunca venderam já tinha sido apontada em [RHughes33/olistSellerFunnelAnalysis](https://github.com/RHughes33/olistSellerFunnelAnalysis); aqui o número é reproduzido a partir do dado bruto.

## Dados e licença

[Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) e [Marketing Funnel](https://www.kaggle.com/datasets/olistbr/marketing-funnel-olist), da Olist, sob CC BY-NC-SA 4.0. Os dados não estão no repositório: `reconcile baixar` busca direto do Kaggle. O código é MIT.
