{{
    config(
        materialized="view"
    )
}}

with daily_prices as (

    select
        symbol,
        bar_interval,
        open_date,

        array_agg(open order by open_time_utc asc limit 1)[offset(0)] as daily_open,
        max(high) as daily_high,
        min(low) as daily_low,
        array_agg(close order by open_time_utc desc limit 1)[offset(0)] as daily_close,

        sum(volume) as daily_volume,
        count(*) as bars_count,

        avg(return_1h) as average_hourly_return,
        avg(rolling_volatility_24h) as average_rolling_volatility_24h,

        min(open_time_utc) as first_bar_utc,
        max(open_time_utc) as last_bar_utc,
        max(loaded_at) as latest_loaded_at
    from {{ ref("fact_price_features") }}
    where
        symbol = 'BTCUSDT'
        and bar_interval = '1h'
    group by
        symbol,
        bar_interval,
        open_date

)

select
    symbol,
    bar_interval,
    open_date,

    daily_open,
    daily_high,
    daily_low,
    daily_close,
    daily_volume,
    bars_count,

    safe_divide(daily_close - daily_open, daily_open) as daily_return,
    average_hourly_return,
    average_rolling_volatility_24h,

    first_bar_utc,
    last_bar_utc,
    latest_loaded_at
from daily_prices
