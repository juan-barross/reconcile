select
    mql_id,
    first_contact_date,
    landing_page_id,
    coalesce(origin, 'unknown') as canal
from {{ ref('stg_olist__marketing_qualified_leads') }}
