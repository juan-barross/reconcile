# O dia em que alguém mexeu na origem

Gerado por `reconcile quebrar` em {data} sobre {base}. Não edite à mão.

Cada cenário reintroduz, numa cópia, uma das causas de divergência da [reunião](a_reuniao.md), pelo dado bruto ou pelo código de um modelo, e roda o `dbt build` inteiro. A tabela mostra os testes que falharam.

Quando um teste do staging falha, o dbt não constrói os modelos que dependem dele. Por isso a quebra na origem aparece num teste só: os marts nunca recebem o dado duplicado.

{tabela}
