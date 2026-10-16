with por_pessoa as (
    select
        customer_unique_id,
        count(*) as ids
    from staging.stg_olist__customers
    group by 1
)

select
    sum(ids) as customer_ids,
    count(*) as pessoas,
    count(*) filter (where ids > 1) as pessoas_que_voltaram,
    sum(ids) - count(*) as contados_a_mais
from por_pessoa
