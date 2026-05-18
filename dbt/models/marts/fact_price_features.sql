{{
    config(
        materialized="table",
        partition_by={
            "field": "open_time_utc",
            "data_type": "timestamp",
            "granularity": "day"
        },
        cluster_by=["symbol", "bar_interval"]
    )
}}

with prices as (

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

        quote_asset_volume,
        number_of_trades,
        taker_buy_base_asset_volume,
        taker_buy_quote_asset_volume,

        loaded_at,
        batch_id
    from {{ ref("fact_prices") }}

),

lagged as (

    select
        *,
        lag(close) over (
            partition by symbol, bar_interval
            order by open_time_utc
        ) as previous_close,

        lag(volume) over (
            partition by symbol, bar_interval
            order by open_time_utc
        ) as previous_volume
    from prices

),

features as (

    select
        *,

        safe_divide(close - previous_close, previous_close) as return_1h,

        case
            when close > 0 and previous_close > 0
                then ln(safe_divide(close, previous_close))
            else null
        end as log_return_1h,

        high - low as price_range,
        safe_divide(high - low, open) as price_range_pct,
        safe_divide(abs(close - open), open) as body_size_pct,

        safe_divide(volume - previous_volume, previous_volume) as volume_change_1h
    from lagged

),

rolling_features as (

    select
        *,

        avg(close) over (
            partition by symbol, bar_interval
            order by open_time_utc
            rows between 23 preceding and current row
        ) as rolling_mean_close_24h,

        stddev_samp(return_1h) over (
            partition by symbol, bar_interval
            order by open_time_utc
            rows between 23 preceding and current row
        ) as rolling_volatility_24h,

        avg(volume) over (
            partition by symbol, bar_interval
            order by open_time_utc
            rows between 23 preceding and current row
        ) as rolling_volume_mean_24h,

        count(*) over (
            partition by symbol, bar_interval
            order by open_time_utc
            rows between 23 preceding and current row
        ) as rolling_window_observations_24h
    from features

)

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

    quote_asset_volume,
    number_of_trades,
    taker_buy_base_asset_volume,
    taker_buy_quote_asset_volume,

    previous_close,
    previous_volume,

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

    loaded_at,
    batch_id
from rolling_features
