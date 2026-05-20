-- Latest market data status for the serving mart.
-- Replace __PROJECT_ID__ before running manually, or use the Makefile target.

select
    symbol,
    bar_interval,
    total_bars,
    total_market_days,
    first_market_bar_utc,
    latest_market_bar_utc,
    latest_loaded_at,
    hours_since_latest_market_bar,
    hours_since_latest_load,
    full_24h_window_ratio
from `__PROJECT_ID__.marts.dashboard_data_status`
order by
    symbol,
    bar_interval;
