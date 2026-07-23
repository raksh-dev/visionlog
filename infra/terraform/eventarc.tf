# 2nd-gen Cloud Run Function for the inference worker, triggered by GCS finalize.
# (Deployed via gcloud functions deploy in deploy.sh; this documents the trigger.)
resource "google_eventarc_trigger" "gcs_finalize" {
  name            = "visionlog-inference-trigger"
  location        = var.region
  service_account = google_service_account.visionlog_sa.email

  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }
  matching_criteria {
    attribute = "bucket"
    value     = google_storage_bucket.images.name
  }

  destination {
    cloud_run_service {
      service = "inference-worker"
      region  = var.region
    }
  }
  depends_on = [google_project_service.enabled]
}
