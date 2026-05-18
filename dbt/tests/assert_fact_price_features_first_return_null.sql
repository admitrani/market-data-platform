with ordered as (

    select
        *,
        row_number() over (
            partition by symbol, bar_interval
            order by open_time_utc
        ) as row_number_ascending
    from {{ ref("fact_price_features") }}

)

select *
from ordered
where row_number_ascending = 1
  and return_1h is not null
