terraform {
  required_version = ">= 1.6.0"

  backend "gcs" {
    bucket = "market-data-platform-adam-dev-tfstate-dev"
    prefix = "market-data-platform/terraform"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}
