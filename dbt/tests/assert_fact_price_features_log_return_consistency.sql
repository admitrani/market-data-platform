select *
from {{ ref("fact_price_features") }}
where return_1h is not null
  and abs(log_return_1h - ln(1 + return_1h)) > 0.000000001
