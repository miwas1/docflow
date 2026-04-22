variable "project_name" {
  description = "Project slug for naming shared resources."
  type        = string
}

variable "environment" {
  description = "Environment name such as dev, staging, or prod."
  type        = string
}

variable "region" {
  description = "Cloud region for the deployment."
  type        = string
}

variable "object_storage_bucket_name" {
  description = "Bucket name for artifact storage."
  type        = string
}

variable "database_instance_name" {
  description = "Managed PostgreSQL instance name."
  type        = string
}

variable "message_broker_name" {
  description = "Message broker resource name."
  type        = string
}

variable "broker_runtime" {
  description = "Broker implementation strategy."
  type        = string
  default     = "rabbitmq"
}

variable "labels" {
  description = "Common labels or tags for cloud resources."
  type        = map(string)
  default     = {}
}
