{{
    config(
        materialized="view"
    )
}}

select
    symbol,
    bar_interval,

    count(*) as total_bars,
    count(distinct open_date) as total_market_days,

    min(open_time_utc) as first_market_bar_utc,
    max(open_time_utc) as latest_market_bar_utc,
    max(loaded_at) as latest_loaded_at,

    timestamp_diff(current_timestamp(), max(open_time_utc), hour) as hours_since_latest_market_bar,
    timestamp_diff(current_timestamp(), max(loaded_at), hour) as hours_since_latest_load,

    countif(rolling_window_observations_24h = 24) as bars_with_full_24h_window,
    safe_divide(
        countif(rolling_window_observations_24h = 24),
        count(*)
    ) as full_24h_window_ratio
from {{ ref("fact_price_features") }}
group by
    symbol,
    bar_interval
