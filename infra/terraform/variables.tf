variable "project_id" {
  type        = string
  description = "GCP project ID (e.g. visionlog-prod)"
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "upload_image" {
  type        = string
  description = "Artifact Registry image for the upload service"
  default     = ""
}

variable "vertex_endpoint_id" {
  type        = string
  description = "Vertex AI endpoint numeric ID (created by model/upload_to_vertex.py)"
  default     = ""
}
