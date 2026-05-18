select
    source,
    dataset as source_dataset,
    symbol,
    `interval` as bar_interval,

    open_time_ms,
    open_time_utc,
    date(open_time_utc) as open_date,

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
from {{ source("raw", "raw_klines") }}
where open_time_utc is not null
