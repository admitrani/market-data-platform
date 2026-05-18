{{
    config(
        materialized="incremental",
        incremental_strategy="merge",
        unique_key=["symbol", "bar_interval", "open_time_utc"],
        partition_by={
            "field": "open_time_utc",
            "data_type": "timestamp",
            "granularity": "day"
        },
        cluster_by=["symbol", "bar_interval"],
        on_schema_change="fail"
    )
}}

with source_data as (

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

    {% if is_incremental() %}
        where open_time_utc >= (
            select coalesce(max(open_time_utc), timestamp('1900-01-01'))
            from {{ this }}
        )
    {% endif %}

)

select *
from source_data
