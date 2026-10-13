-- Um dia por linha. O MetricFlow usa esta tabela para agrupar por mês, semana
-- etc. e para preencher dias sem movimento. Cobre a base com folga.

{{ config(materialized='table', schema='marts') }}

select cast(d as date) as date_day
from generate_series(date '2016-01-01', date '2019-12-31', interval 1 day) as t (d)
