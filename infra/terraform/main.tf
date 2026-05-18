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