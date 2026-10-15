with fonte as (
    select * from {{ source('olist', 'products') }}
)

select
    product_id,
    product_category_name as category_name,
    cast(product_name_lenght as integer) as name_length,
    cast(product_description_lenght as integer) as description_length,
    cast(product_photos_qty as integer) as photos_qty,
    cast(product_weight_g as integer) as weight_g,
    cast(product_length_cm as integer) as length_cm,
    cast(product_height_cm as integer) as height_cm,
    cast(product_width_cm as integer) as width_cm
from fonte
