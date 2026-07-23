terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.30"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  apis = [
    "run.googleapis.com",
    "cloudfunctions.googleapis.com",
    "storage.googleapis.com",
    "firestore.googleapis.com",
    "eventarc.googleapis.com",
    "aiplatform.googleapis.com",
    "apigateway.googleapis.com",
    "servicecontrol.googleapis.com",
    "cloudbuild.googleapis.com",
    "secretmanager.googleapis.com",
    "logging.googleapis.com",
    "artifactregistry.googleapis.com",
  ]
}

resource "google_project_service" "enabled" {
  for_each           = toset(local.apis)
  service            = each.value
  disable_on_destroy = false
}

# Least-privilege service account shared by both services.
resource "google_service_account" "visionlog_sa" {
  account_id   = "visionlog-sa"
  display_name = "VisionLog service account"
}

locals {
  sa_roles = [
    "roles/storage.objectAdmin",
    "roles/datastore.user",
    "roles/run.invoker",
    "roles/aiplatform.user",
    "roles/logging.logWriter",
    "roles/secretmanager.secretAccessor",
  ]
}

resource "google_project_iam_member" "sa_roles" {
  for_each = toset(local.sa_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.visionlog_sa.email}"
}
