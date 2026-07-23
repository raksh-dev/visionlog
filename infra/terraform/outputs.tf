output "images_bucket" {
  value = google_storage_bucket.images.name
}

output "models_bucket" {
  value = google_storage_bucket.models.name
}

output "upload_service_url" {
  value = google_cloud_run_v2_service.upload.uri
}

output "api_gateway_url" {
  value = google_api_gateway_gateway.visionlog.default_hostname
}

output "service_account_email" {
  value = google_service_account.visionlog_sa.email
}
