resource "google_firestore_database" "default" {
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
  depends_on  = [google_project_service.enabled]
}

# Composite indexes for the dashboard queries.
resource "google_firestore_index" "status_uploaded" {
  collection = "predictions"
  fields {
    field_path = "status"
    order      = "ASCENDING"
  }
  fields {
    field_path = "uploadedAt"
    order      = "DESCENDING"
  }
}

resource "google_firestore_index" "uploaded_desc" {
  collection = "predictions"
  fields {
    field_path = "uploadedAt"
    order      = "DESCENDING"
  }
  fields {
    field_path = "__name__"
    order      = "DESCENDING"
  }
}
