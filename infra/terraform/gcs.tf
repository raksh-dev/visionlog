resource "google_storage_bucket" "images" {
  name                        = "visionlog-images-${var.project_id}"
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning { enabled = false }

  lifecycle_rule {
    condition { age = 90 }
    action { type = "Delete" }
  }
}

resource "google_storage_bucket" "models" {
  name                        = "visionlog-models-${var.project_id}"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
}
