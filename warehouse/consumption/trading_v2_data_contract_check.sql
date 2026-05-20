-- Data contract check for downstream trading/ML consumers.
-- Replace __PROJECT_ID__ before running manually.

select
    symbol,
    bar_interval,

    count(*) as rows_count,
    min(open_time_utc) as first_open_time_utc,
    max(open_time_utc) as latest_open_time_utc,

    countif(close is null) as null_close_count,
    countif(volume is null) as null_volume_count,
    countif(return_1h is null) as null_return_1h_count,
    countif(rolling_window_observations_24h = 24) as full_rolling_window_rows,

    safe_divide(
        countif(rolling_window_observations_24h = 24),
        count(*)
    ) as full_rolling_window_ratio
from `__PROJECT_ID__.marts.dashboard_price_timeseries`
group by
    symbol,
    bar_interval;
