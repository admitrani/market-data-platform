select
    symbol,
    bar_interval,
    open_time_utc,
    count(*) as row_count
from {{ ref("fact_prices") }}
group by symbol, bar_interval, open_time_utc
having count(*) > 1
