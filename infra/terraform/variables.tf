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