select *
from {{ ref("stg_klines") }}
where high < greatest(open, close)
   or low > least(open, close)
