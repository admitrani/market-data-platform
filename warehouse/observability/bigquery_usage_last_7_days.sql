-- BigQuery query usage over the last 7 days.
-- This is used as a cost observability query.
-- Replace __PROJECT_ID__ before running manually, or use the Makefile target.

select
    date(creation_time) as usage_date,
    user_email,
    count(*) as query_jobs,
    round(sum(total_bytes_processed) / pow(1024, 2), 2) as processed_mib,
    round(sum(total_bytes_billed) / pow(1024, 2), 2) as billed_mib,
    round(sum(total_bytes_billed) / pow(1024, 4), 6) as billed_tib
from `__PROJECT_ID__.region-europe-west1.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
where creation_time >= timestamp_sub(current_timestamp(), interval 7 day)
  and job_type = 'QUERY'
group by
    usage_date,
    user_email
order by
    usage_date desc,
    billed_mib desc;
