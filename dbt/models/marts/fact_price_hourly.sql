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

        loaded_at,
        batch_id
    from {{ ref("stg_klines") }}

),

with_returns as (

    select
        *,
        lag(close) over (
            partition by symbol, bar_interval
            order by open_time_utc
        ) as previous_close
    from prices

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

    safe_divide(close - previous_close, previous_close) as return_1h,

    loaded_at,
    batch_id
from with_returns
