output "raw_bucket_name" {
  description = "Name of the raw data bucket"
  value       = google_storage_bucket.raw_data.name
}

output "raw_bucket_url" {
  description = "Google Cloud Storage URL for the raw data bucket"
  value       = "gs://${google_storage_bucket.raw_data.name}"
}