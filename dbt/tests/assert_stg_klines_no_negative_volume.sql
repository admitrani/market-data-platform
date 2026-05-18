select *
from {{ ref("stg_klines") }}
where volume < 0
   or quote_asset_volume < 0
