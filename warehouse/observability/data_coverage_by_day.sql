-- Daily coverage check for market bars.
-- For a 1h crypto feed, a complete UTC day should usually contain 24 bars.

select
    symbol,
    bar_interval,
    open_date,
    count(*) as bars_count,
    min(open_time_utc) as first_bar_utc,
    max(open_time_utc) as last_bar_utc,
    case
        when count(*) = 24 then 'complete'
        else 'incomplete'
    end as coverage_status
from `__PROJECT_ID__.marts.fact_prices`
group by
    symbol,
    bar_interval,
    open_date
order by
    open_date desc,
    symbol,
    bar_interval;
