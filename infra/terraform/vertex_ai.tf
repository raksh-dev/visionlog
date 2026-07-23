# Vertex AI model + endpoint are created imperatively by model/upload_to_vertex.py
# (the Python SDK handles SavedModel upload + deployment more cleanly than TF).
# This file just records the endpoint ID as a Secret Manager secret for the worker.
resource "google_secret_manager_secret" "vertex_endpoint" {
  secret_id = "visionlog-vertex-endpoint-id"
  replication { auto {} }
}

resource "google_secret_manager_secret_version" "vertex_endpoint" {
  count       = var.vertex_endpoint_id == "" ? 0 : 1
  secret      = google_secret_manager_secret.vertex_endpoint.id
  secret_data = var.vertex_endpoint_id
}

resource "google_secret_manager_secret" "api_key" {
  secret_id = "visionlog-api-key"
  replication { auto {} }
}
