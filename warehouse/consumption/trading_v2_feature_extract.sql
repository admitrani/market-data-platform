-- Feature extraction query for downstream trading/ML research systems.
-- Replace __PROJECT_ID__ before running manually, or use this as a template
-- for Python BigQuery client reads.

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
from `__PROJECT_ID__.marts.dashboard_price_timeseries`
where symbol = 'BTCUSDT'
  and bar_interval = '1h'
order by
    open_time_utc;
