terraform {
  required_version = ">= 1.6.0"
}

locals {
  foundation_contract = {
    project_name               = var.project_name
    environment                = var.environment
    region                     = var.region
    object_storage_bucket_name = var.object_storage_bucket_name
    database_instance_name     = var.database_instance_name
    message_broker_name        = var.message_broker_name
    broker_runtime             = var.broker_runtime
    labels                     = var.labels
  }
}

output "foundation_contract" {
  description = "Canonical Phase 1 managed-foundation contract."
  value       = local.foundation_contract
}
