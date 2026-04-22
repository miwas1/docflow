# Terraform Foundation

Terraform in this repository is for managed service foundations only. It captures the baseline cloud contract for the document platform and is not Kubernetes.

## Layout

- `modules/platform_foundation` defines the shared foundation inputs and outputs.
- `environments/aws-dev` wires the module for S3, RDS PostgreSQL, and Amazon MQ RabbitMQ.
- `environments/gcp-dev` wires the module for GCS, Cloud SQL PostgreSQL, and a `self-managed-rabbitmq` broker runtime strategy.

## Usage Notes

- The module is intentionally focused on storage, database, and broker foundations.
- Application compute, autoscaling, and higher-level deployment orchestration are deferred to later phases.
- Environment tfvars examples document the expected inputs without assuming Kubernetes.
