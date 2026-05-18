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
from {{ ref("int_klines_normalized") }}
