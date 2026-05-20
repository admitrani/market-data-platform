resource "google_storage_bucket" "raw_data" {
  name          = var.raw_bucket_name
  location      = var.gcp_region
  force_destroy = false

  uniform_bucket_level_access = true

  labels = {
    environment = var.environment
    layer       = "raw"
    project     = "market-data-platform"
  }
}

locals {
  bigquery_datasets = toset([
    "raw",
    "staging",
    "intermediate",
    "marts",
    "ci"
  ])
}

resource "google_bigquery_dataset" "datasets" {
  for_each = local.bigquery_datasets

  dataset_id = each.key
  location   = var.bigquery_location

  labels = {
    environment = var.environment
    layer       = each.key
    project     = "market-data-platform"
  }
}

resource "google_service_account" "pipeline_runner" {
  account_id   = var.pipeline_service_account_id
  display_name = "Market Data Platform Pipeline Runner"
  description  = "Service account used by ingestion, dbt and orchestration workloads"
}

resource "google_storage_bucket_iam_member" "pipeline_raw_bucket_object_admin" {
  bucket = google_storage_bucket.raw_data.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.pipeline_runner.email}"
}

resource "google_project_iam_member" "pipeline_bigquery_job_user" {
  project = var.gcp_project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.pipeline_runner.email}"
}

resource "google_bigquery_dataset_iam_member" "pipeline_bigquery_data_editor" {
  for_each = google_bigquery_dataset.datasets

  project    = var.gcp_project_id
  dataset_id = each.value.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.pipeline_runner.email}"
}

resource "google_secret_manager_secret" "external_api_key" {
  secret_id = var.secret_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    project     = "market-data-platform"
  }
}

resource "google_secret_manager_secret_iam_member" "pipeline_secret_accessor" {
  project   = var.gcp_project_id
  secret_id = google_secret_manager_secret.external_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.pipeline_runner.email}"
}
