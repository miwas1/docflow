terraform {
  required_version = ">= 1.6.0"
}

module "platform_foundation" {
  source                     = "../../modules/platform_foundation"
  project_name               = "doc-platform"
  environment                = "aws-dev"
  region                     = "us-east-1"
  object_storage_bucket_name = "doc-platform-artifacts-dev"
  database_instance_name     = "doc-platform-rds-dev"
  message_broker_name        = "doc-platform-amazon-mq-dev"
  broker_runtime             = "amazon-mq-rabbitmq"
  labels = {
    cloud   = "aws"
    storage = "s3"
    db      = "rds-postgresql"
    broker  = "Amazon MQ"
  }
}
