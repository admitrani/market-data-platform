with source_data as (

    select
        source,
        source_dataset,
        symbol,
        bar_interval,

        open_time_ms,
        open_time_utc,
        open_date,

        open,
        high,
        low,
        close,
        volume,

        close_time_ms,
        close_time_utc,

        quote_asset_volume,
        number_of_trades,
        taker_buy_base_asset_volume,
        taker_buy_quote_asset_volume,

        loaded_at,
        batch_id,

        row_number() over (
            partition by symbol, bar_interval, open_time_utc
            order by loaded_at desc
        ) as row_number_latest
    from {{ ref("stg_klines") }}

),

deduplicated as (

    select
        source,
        source_dataset,
        symbol,
        bar_interval,

        open_time_ms,
        open_time_utc,
        open_date,

        open,
        high,
        low,
        close,
        volume,

        close_time_ms,
        close_time_utc,

        quote_asset_volume,
        number_of_trades,
        taker_buy_base_asset_volume,
        taker_buy_quote_asset_volume,

        loaded_at,
        batch_id
    from source_data
    where row_number_latest = 1

)

select *
from deduplicated
