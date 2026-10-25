# Reconcile

[![CI](https://github.com/juan-barross/Reconcile-/actions/workflows/ci.yml/badge.svg)](https://github.com/juan-barross/Reconcile-/actions/workflows/ci.yml)
[![Resultado no dado real](https://github.com/juan-barross/Reconcile-/actions/workflows/resultado.yml/badge.svg)](https://github.com/juan-barross/Reconcile-/actions/workflows/resultado.yml)

Marketing, vendas, financeiro e operação da Olist respondem à mesma pergunta com números diferentes. Este projeto reproduz a divergência com os dados reais da Olist, mede cada causa, monta uma camada única de métricas em dbt e MetricFlow e mostra que os testes pegam a divergência quando ela volta.

Março de 2018, "quantos lojistas conquistamos?":

| marketing | vendas | operação | camada única |
|---:|---:|---:|---:|
| 167 | 147 | 25 | 147 contratados, 25 ativados |

Marketing conta pela data do primeiro contato, vendas pela do contrato e operação pela primeira venda. A camada única dá um nome a cada número e registra a regra de data no [contrato de métricas](docs/contrato_de_metricas.md).

## Ver o resultado

Sem instalar nada:

- Clique no selo *Resultado no dado real* e abra a última execução. A cada push, o GitHub baixa a Olist, roda o pipeline, quebra a origem de propósito e publica o resultado na própria página.
- Ou abra o projeto no navegador e rode `uv run reconcile tudo`:

  [![Abrir no GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/juan-barross/Reconcile-?quickstart=1)

Ou leia as páginas geradas com o dado real:

| página | conteúdo |
|---|---|
| [Veredito](docs/veredito.md) | se as pontes entre as áreas fecham |
| [A reunião](docs/a_reuniao.md) | a resposta de cada área e a causa de cada diferença, no centavo |
| [Painel](docs/painel.md) | as oito métricas oficiais mês a mês |
| [Quebras](docs/o_dia_que_mexeram_na_origem.md) | cinco divergências reintroduzidas e o teste que pegou cada uma |
| [Agente](docs/agente.md) | 48 perguntas a um agente de IA, com e sem a camada única |
| [Growth Review](docs/growth_review.md) | quanto vale um lead de cada canal e três recomendações |
| [Auditoria](docs/auditoria.md) | o que a origem tem de estranho |

## O que os números mostram

- Busca converte 12% dos leads, social 5,7% e e-mail 3,7%. A receita por contrato em 180 dias é igual entre canais, dentro do ruído.
- 47% dos lojistas contratados não vendem nada em 180 dias.
- 23% dos contratos não têm canal registrado, e esse grupo é o que mais converte.

O agente de IA respondeu às mesmas 48 perguntas em duas versões. A versão A escreve SQL no dado bruto e acertou 25 (52%). Errou onde as áreas também divergem: lojistas ativados, receita bruta e pedidos válidos. A versão B só usa as métricas do contrato e acertou as 48, gastando menos (US$ 0,55 contra US$ 0,84).

## Rodar na sua máquina

Precisa de Python 3.12 e [uv](https://docs.astral.sh/uv/). Não precisa de Docker, conta no Kaggle nem chave de API.

```bash
git clone https://github.com/juan-barross/Reconcile-.git reconcile
cd reconcile
uv sync
uv run reconcile tudo
```

`reconcile tudo` baixa a Olist (cerca de 45 MB), roda o dbt e gera os relatórios em `docs/`. Com `--amostra`, usa uma base sintética de 30 pedidos, sem rede, e grava em `data/amostra/`. Os testes rodam com `uv run pytest`.

| comando | o que faz |
|---|---|
| `baixar`, `carregar` | baixa os 11 CSVs e carrega no DuckDB como texto |
| `auditar` | checa chaves, órfãos e datas da origem |
| `dbt` | roda modelos e testes |
| `reuniao`, `veredito` | a resposta de cada área e se as pontes fecham |
| `painel`, `metricas` | as métricas do contrato pelos marts e pelo MetricFlow |
| `quebrar` | reintroduz cada divergência numa cópia e mostra o teste que a pega |
| `crescimento` | valor por lead e ativação por canal |
| `perguntar`, `avaliar` | o agente; são os únicos que pedem chave (`ANTHROPIC_API_KEY` ou `OPENROUTER_API_KEY`) |

## Como funciona

```text
CSVs -> raw (texto) -> staging (tipos) -> intermediate -> marts (contrato) -> MetricFlow
            |                                                 |
        auditoria                                 painel, reunião, agente
```

- `staging`: só tipos e nomes.
- `intermediate` e `marts`: as regras do contrato de métricas, com contrato de modelo em todo mart.
- `semantic`: as oito métricas no MetricFlow; um teste confere que batem com os marts.
- `departamentos/`: a consulta que cada área faria sozinha.
- `reconcile/`: o pacote Python, com as consultas em `sql/`, o texto dos relatórios em `modelos/` e as checagens em YAML.

## O que deu errado no caminho

- O teste `clientes_contados_por_pessoa` comparava a dimensão com o fato de pedidos. Trocar a chave mudava os dois juntos e ele continuava verde. Descobri quando a quebra de propósito passou calada; hoje ele compara com o staging.
- A amostra sintética escondia essa quebra, porque quem comprava duas vezes só tinha pedido cancelado. Também tinha lojista vendendo antes do contrato e juros acima de 1% da receita, coisas que o dado real não tem.
- Eu queria uma janela de 12 meses, mas nenhum contrato tem 12 meses observados. Ficou em 180 dias.
- O dbt no mesmo processo segurava o arquivo do DuckDB. Passou a rodar em subprocesso.
- A CI falhou duas vezes no GitHub e passava na minha máquina: uma regra de estilo SQL e o `quebrar` copiando o projeto antes de instalar os pacotes do dbt.
- O painel no Metabase pedia Docker numa máquina de 4 GB. Virou um painel estático ([ADR 0004](docs/adr/0004-painel-estatico-no-lugar-do-metabase.md)).

Outras decisões: [DuckDB](docs/adr/0001-duckdb-como-armazem.md), [MetricFlow](docs/adr/0002-metricflow-como-camada-semantica.md) e [Metabase](docs/adr/0003-metabase-como-bi.md) (substituída).

## Referências e licença

[Samir-AISS/olist-ecommerce-data-platform](https://github.com/Samir-AISS/olist-ecommerce-data-platform) serviu de referência para as camadas e os testes; nenhum código foi copiado. A taxa de lojistas que nunca venderam já aparecia em [RHughes33/olistSellerFunnelAnalysis](https://github.com/RHughes33/olistSellerFunnelAnalysis).

Dados: [Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) e [Marketing Funnel](https://www.kaggle.com/datasets/olistbr/marketing-funnel-olist), da Olist, sob CC BY-NC-SA 4.0. Não ficam no repositório. Código sob MIT.
