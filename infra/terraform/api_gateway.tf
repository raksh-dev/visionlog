resource "google_api_gateway_api" "visionlog" {
  provider = google
  api_id   = "visionlog-api"
}

resource "google_api_gateway_api_config" "visionlog" {
  provider      = google
  api           = google_api_gateway_api.visionlog.api_id
  api_config_id = "visionlog-config"

  openapi_documents {
    document {
      path = "openapi.yaml"
      # Render the upload-service openapi.yaml with the Cloud Run URL substituted
      # for BACKEND_URL, then base64-encode it here in CI.
      contents = filebase64("${path.module}/openapi_rendered.yaml")
    }
  }
  lifecycle { create_before_destroy = true }
}

resource "google_api_gateway_gateway" "visionlog" {
  provider   = google
  region     = var.region
  api_config = google_api_gateway_api_config.visionlog.id
  gateway_id = "visionlog-gateway"
}
