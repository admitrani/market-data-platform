with date_bounds as (

    select
        min(open_date) as min_date,
        max(open_date) as max_date
    from {{ ref("int_klines_normalized") }}

),

calendar as (

    select calendar_date
    from date_bounds,
        unnest(generate_date_array(min_date, max_date)) as calendar_date

)

select
    calendar_date,
    extract(year from calendar_date) as calendar_year,
    extract(quarter from calendar_date) as calendar_quarter,
    extract(month from calendar_date) as calendar_month,
    extract(day from calendar_date) as calendar_day,
    extract(dayofweek from calendar_date) as day_of_week,
    format_date('%A', calendar_date) as day_name,
    calendar_date = current_date() as is_current_date
from calendar
