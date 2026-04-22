terraform {
  required_version = ">= 1.6.0"
}

module "platform_foundation" {
  source                     = "../../modules/platform_foundation"
  project_name               = "doc-platform"
  environment                = "gcp-dev"
  region                     = "us-central1"
  object_storage_bucket_name = "doc-platform-artifacts-dev"
  database_instance_name     = "doc-platform-cloud-sql-dev"
  message_broker_name        = "doc-platform-rabbitmq-dev"
  broker_runtime             = "self-managed-rabbitmq"
  labels = {
    cloud   = "gcp"
    storage = "gcs"
    db      = "Cloud SQL"
    broker  = "self-managed-rabbitmq"
  }
}
