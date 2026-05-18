with ordered as (

    select
        symbol,
        bar_interval,
        open_time_utc,
        lag(open_time_utc) over (
            partition by symbol, bar_interval
            order by open_time_utc
        ) as previous_open_time_utc
    from {{ ref("fact_prices") }}

),

gaps as (

    select *
    from ordered
    where previous_open_time_utc is not null
      and timestamp_diff(open_time_utc, previous_open_time_utc, hour) != 1

)

select *
from gaps
