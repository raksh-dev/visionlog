resource "google_cloud_run_v2_service" "upload" {
  name     = "upload-service"
  location = var.region

  template {
    service_account = google_service_account.visionlog_sa.email
    scaling {
      min_instance_count = 1
      max_instance_count = 10
    }
    max_instance_request_concurrency = 80
    timeout                          = "30s"

    containers {
      image = var.upload_image
      resources {
        limits = { cpu = "1", memory = "512Mi" }
      }
      ports { container_port = 8080 }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCS_BUCKET_NAME"
        value = google_storage_bucket.images.name
      }
      env {
        name  = "FIRESTORE_COLLECTION"
        value = "predictions"
      }
      env {
        name  = "API_KEY_SECRET_NAME"
        value = "visionlog-api-key"
      }
    }
  }
}
