select *
from {{ ref("fact_price_features") }}
where price_range < 0
   or price_range_pct < 0
   or body_size_pct < 0
   or rolling_window_observations_24h < 1
   or rolling_window_observations_24h > 24
