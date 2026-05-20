{{
    config(
        materialized="view"
    )
}}

select
    symbol,
    bar_interval,
    open_time_utc,
    open_date,

    open,
    high,
    low,
    close,
    volume,

    return_1h,
    log_return_1h,
    price_range,
    price_range_pct,
    body_size_pct,
    volume_change_1h,

    rolling_mean_close_24h,
    rolling_volatility_24h,
    rolling_volume_mean_24h,
    rolling_window_observations_24h,

    loaded_at
from {{ ref("fact_price_features") }}
where
    symbol = 'BTCUSDT'
    and bar_interval = '1h'
