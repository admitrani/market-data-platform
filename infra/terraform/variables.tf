variable "gcp_project_id" {
  description = "Google Cloud project ID"
  type        = string
}

variable "gcp_region" {
  description = "Default Google Cloud region"
  type        = string
  default     = "europe-west1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "raw_bucket_name" {
  description = "Name of the raw data Google Cloud Storage bucket"
  type        = string
}

variable "bigquery_location" {
  description = "BigQuery dataset location"
  type        = string
  default     = "europe-west1"
}

variable "pipeline_service_account_id" {
  description = "Service account ID for running data platform pipelines"
  type        = string
  default     = "mdp-pipeline-dev"
}

variable "secret_id" {
  description = "Secret Manager secret ID for external API credentials"
  type        = string
  default     = "market-data-api-key-dev"
}
