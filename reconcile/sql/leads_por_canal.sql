select
    l.canal,
    count(*) as leads,
    count(j.mql_id) as contratos
from marts.dim_leads as l
left join marts.fct_jornada_lojista as j on l.mql_id = j.mql_id
group by 1
order by 1
