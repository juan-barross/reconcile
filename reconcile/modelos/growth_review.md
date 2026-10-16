# Growth Review

Gerado por `reconcile crescimento` a partir da camada única. Não edite os números à mão.

## Em uma frase

O canal decide **quantos** leads viram contrato, não **quanto** cada contrato vende: a receita por contrato nos primeiros {janela} dias é a mesma em todos os canais dentro do ruído, e um lead de busca vale cerca de {vezes} vezes um de rede social. Mas o maior vazamento do funil não está na aquisição: {sem_venda} dos lojistas contratados não fazem nenhuma venda em {janela} dias.

## Recomendações

1. **Concentrar a verba em busca (paga e orgânica) e rever social e e-mail.** Busca converte {conv_paga} e {conv_organica} dos leads; social converte {conv_social} e e-mail {conv_email}, {sobre_ic}. Como a receita por contrato não muda com o canal, a escolha do canal é uma escolha de conversão.

2. **Tratar ativação como meta, com o mesmo peso da aquisição.** Só {ativ_90} dos contratados vendem em 90 dias e {ativ_janela} em {janela}: a curva desacelera depois de 90 dias, com só mais {pontos} pontos nos 90 dias seguintes. Um programa de onboarding nos primeiros 90 dias ataca o ponto em que o lojista ainda pode ser recuperado. Cada contrato que ativa vende, em média, cerca de {venda_por_ativado} nos primeiros {janela} dias.

3. **Consertar o registro de origem antes de decidir verba.** {leads_sem_canal} dos leads e {contratos_sem_canal} dos contratos não têm canal (`unknown`), e é justamente o grupo que mais converte ({conv_sem_canal}). Se forem leads de indicação ou de vendas internas mal registrados, o canal mais eficiente está invisível. Tornar o campo obrigatório no CRM custa pouco e destrava a recomendação 1.

## Valor de um lead, por canal

Valor = P(lead vira contrato) × receita bruta média de um contrato nos {janela} dias seguintes. A conversão usa os {total_leads} leads; a receita usa só os contratos com {janela} dias observados por inteiro. As duas partes são encolhidas para a média geral e o intervalo vem de 2.000 reamostras (bootstrap).

![Conversão por canal](img/conversao_por_canal.png)

{valor}

**Por que a receita por contrato é igual entre canais.** Antes do encolhimento as médias variam muito (o `unknown` tem {media_bruta_sem_canal}, mas um único lojista responde por {concentracao} da receita do canal e a mediana é {mediana_sem_canal}). Ainda assim, a variação entre canais é menor que a esperada só pelo acaso com tão poucos contratos observados (de 1 a {max_observados} por canal). O melhor palpite para qualquer canal é a média geral, {receita_por_contrato}.

**Sensibilidade à taxa da Olist.** A base não informa a comissão que a Olist cobra do lojista, então a receita da Olist é uma premissa. Como ela multiplica o valor de todos os canais pelo mesmo número, a ordem dos canais não muda com a taxa; muda só o valor absoluto:

{sensibilidade}

## Ativação: do contrato à primeira venda

![Ativação por canal](img/ativacao_por_canal.png)

{ativacao}

Canais com menos de 15 contratos ficam fora da tabela. As frações usam Kaplan-Meier: contrato assinado perto do fim da base conta enquanto foi observado e sai da conta depois, em vez de entrar como "nunca vendeu".

## Premissas e limites

- **Janela de {janela} dias.** Nenhum contrato tem 12 meses observados (o mais antigo é de dez/2017 e a observação termina em 31/08/2018).
- **Receita é a do lojista (GMV), não a da Olist.** A receita da Olist depende da taxa, que é premissa.
- **Correlação, não efeito causal.** Um canal que converte mais pode atrair lojistas diferentes; o que a análise sustenta é de onde os contratos vieram, não o que aconteceria mudando a verba.
- **Pouca amostra em canais pequenos.** {total_contratos} contratos em {n_canais} canais; por isso o encolhimento e os intervalos.
