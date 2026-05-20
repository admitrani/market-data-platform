output "raw_bucket_name" {
  description = "Name of the raw data bucket"
  value       = google_storage_bucket.raw_data.name
}

output "raw_bucket_url" {
  description = "Google Cloud Storage URL for the raw data bucket"
  value       = "gs://${google_storage_bucket.raw_data.name}"
}

output "bigquery_datasets" {
  description = "Created BigQuery dataset IDs"
  value       = keys(google_bigquery_dataset.datasets)
}

output "pipeline_service_account_email" {
  description = "Pipeline service account email"
  value       = google_service_account.pipeline_runner.email
}

output "external_api_secret_id" {
  description = "Secret Manager secret ID for external API credentials"
  value       = google_secret_manager_secret.external_api_key.secret_id
}
