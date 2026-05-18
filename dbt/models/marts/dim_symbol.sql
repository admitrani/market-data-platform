select
    symbol,
    'crypto' as asset_class,
    'Binance Spot' as exchange,
    'USDT' as quote_currency,
    min(open_time_utc) as first_seen_at,
    max(open_time_utc) as last_seen_at,
    count(*) as observed_bars
from {{ ref("int_klines_normalized") }}
group by symbol
