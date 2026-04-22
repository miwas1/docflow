# Document Classification and Extraction Inference Platform — Definition of Done Checklist

Use this checklist before calling the platform complete. Every item should be demonstrably verifiable through automated tests, documented manual validation, or production-readiness evidence.

---

## 1. Scope and Product Acceptance

- [ ] The platform accepts PDFs and supported image formats through a documented API.
- [ ] The platform processes uploaded documents asynchronously rather than inline with the request.
- [ ] The platform runs OCR and document classification as distinct pipeline stages.
- [ ] OCR and classification can be invoked as independent inference services.
- [ ] Results can be retrieved through polling APIs, webhooks, or a dashboard.
- [ ] The platform tracks throughput, failures, and model/version usage.
- [ ] The platform supports model version updates without downtime.
- [ ] The supported file types, file size limits, page limits, timeout limits, and SLA assumptions are documented.
- [ ] Success criteria for MVP and non-MVP features are explicitly documented.

---

## 2. API Contract Tests

### Upload API
- [ ] Upload endpoint accepts valid PDF files.
- [ ] Upload endpoint accepts valid supported image files.
- [ ] Upload endpoint rejects unsupported MIME types with correct status codes and error bodies.
- [ ] Upload endpoint rejects malformed requests.
- [ ] Upload endpoint enforces configured max file size.
- [ ] Upload endpoint returns a stable `job_id` and `document_id` for accepted requests.
- [ ] Upload endpoint is idempotent when the same idempotency key is reused.
- [ ] Duplicate uploads are handled according to documented behavior.
- [ ] Upload endpoint persists metadata required to trace the job.

### Job Status API
- [ ] Job status endpoint returns the correct state for queued jobs.
- [ ] Job status endpoint returns the correct state for running jobs.
- [ ] Job status endpoint returns the correct state for completed jobs.
- [ ] Job status endpoint returns the correct state for failed jobs.
- [ ] Job status endpoint returns progress and current stage when available.
- [ ] Job status endpoint returns a consistent schema across all states.
- [ ] Job status endpoint handles unknown job IDs correctly.

### Results API
- [ ] Results endpoint returns persisted OCR and classification outputs for completed jobs.
- [ ] Results endpoint does not expose partial/corrupt data for incomplete jobs unless explicitly supported.
- [ ] Results endpoint returns model versions used for OCR and classification.
- [ ] Results endpoint returns confidence fields where expected.
- [ ] Results endpoint handles missing/failed results correctly.

### Webhook API / Registration
- [ ] Webhook registration validates destination URLs.
- [ ] Webhook events use a documented payload schema.
- [ ] Webhook signatures or verification secrets are supported.
- [ ] Webhook registration supports update, disable, and delete flows if included in scope.

---

## 3. Input Validation and Security Tests

- [ ] Uploaded files are scanned or validated against malicious or malformed input handling policy.
- [ ] Corrupt PDFs do not crash workers or services.
- [ ] Password-protected or encrypted PDFs are handled according to documented policy.
- [ ] Extremely large page-count documents are handled safely.
- [ ] File extension spoofing is detected via content-type or file signature checks.
- [ ] Invalid image encodings are rejected safely.
- [ ] Path traversal and unsafe filename handling are prevented.
- [ ] Request authentication and authorization are enforced for all protected endpoints.
- [ ] Tenant isolation is enforced where multi-tenancy is supported.
- [ ] Secrets are not exposed in logs, responses, or metrics.
- [ ] Rate limiting or abuse protection is in place if required.

---

## 4. Storage and Data Persistence Tests

- [ ] Raw uploaded files are persisted to object storage successfully.
- [ ] Derived artifacts (page images, OCR JSON, extracted text, classification output) are stored successfully.
- [ ] Job metadata is persisted in the database.
- [ ] Job state transitions are persisted durably.
- [ ] Re-reading stored artifacts reproduces expected results.
- [ ] Storage failures are retried or surfaced correctly.
- [ ] Orphaned artifacts are detectable and handled by cleanup policy.
- [ ] Data retention and deletion behavior is documented and testable.
- [ ] Audit-relevant metadata is stored for each processed job.

---

## 5. Queue / Workflow / Async Processing Tests

- [ ] Accepted uploads produce an asynchronous job message or workflow execution.
- [ ] Jobs move through the expected state machine in order.
- [ ] Pipeline stages can be retried independently when failures occur.
- [ ] Worker restarts do not lose in-flight durable jobs beyond documented guarantees.
- [ ] Duplicate message delivery does not produce duplicate final side effects.
- [ ] Poison messages are isolated or routed to a dead-letter mechanism.
- [ ] Backpressure is handled gracefully under load.
- [ ] Jobs can be canceled if cancellation is in scope.
- [ ] Timeouts are enforced for long-running stages.
- [ ] Workflow recovery after service restart is verified.

---

## 6. Preprocessing and Document Handling Tests

- [ ] Multi-page PDFs are split/processed correctly.
- [ ] Single-page PDFs are handled correctly.
- [ ] Single image uploads are handled correctly.
- [ ] Rotated pages are handled correctly or flagged according to policy.
- [ ] Low-resolution images are handled according to expected quality policy.
- [ ] Blank pages do not break the pipeline.
- [ ] Mixed-content documents (text pages + scanned pages) are handled correctly.
- [ ] Document page ordering is preserved end-to-end.
- [ ] Page count metadata is accurate.

---

## 7. OCR Inference Tests

- [ ] OCR service health checks pass.
- [ ] OCR inference succeeds on representative PDFs.
- [ ] OCR inference succeeds on representative image inputs.
- [ ] OCR output includes extracted text in the documented format.
- [ ] OCR output includes confidence fields if promised by the API.
- [ ] OCR output includes layout/bounding box data if promised by the API.
- [ ] OCR timeouts fail cleanly and update job state appropriately.
- [ ] OCR service unavailability is retried or surfaced correctly.
- [ ] OCR outputs are traceable to a specific model version.
- [ ] OCR service can scale horizontally without incorrect shared-state behavior.

---

## 8. Classification Inference Tests

- [ ] Classification service health checks pass.
- [ ] Classification runs successfully on OCR-derived text and/or document features.
- [ ] Classification returns a valid label from the configured label set.
- [ ] Classification returns a confidence score if expected.
- [ ] Low-confidence documents are handled according to policy.
- [ ] Unsupported or unclassifiable documents map to `unknown`/`other` according to policy.
- [ ] Classification service failure updates job state correctly.
- [ ] Classification outputs are traceable to a specific model version.
- [ ] Classification service can scale horizontally.
- [ ] Classification does not rely on mutable local state that breaks under concurrency.

---

## 9. End-to-End Pipeline Tests

- [ ] A valid PDF can be uploaded, processed asynchronously, and returned with OCR + classification results.
- [ ] A valid image can be uploaded, processed asynchronously, and returned with OCR + classification results.
- [ ] End-to-end processing succeeds for representative sample documents from each supported class.
- [ ] End-to-end processing preserves correlation IDs / trace IDs across services.
- [ ] End-to-end processing records all stage timings.
- [ ] End-to-end processing stores final outputs in durable storage.
- [ ] End-to-end processing updates job state to `completed` only after all required stages succeed.
- [ ] End-to-end failure paths update job state to `failed` or `partial` correctly.

---

## 10. Failure Handling and Recovery Tests

- [ ] Transient network failures between workers and inference services are retried.
- [ ] Permanent failures surface useful error codes/messages.
- [ ] Partial pipeline failures do not corrupt completed prior-stage outputs.
- [ ] Callback delivery failures are retried.
- [ ] Repeated callback failures move to dead-letter or terminal failure state.
- [ ] DB outages fail safely according to the documented resilience model.
- [ ] Object storage outages fail safely according to the documented resilience model.
- [ ] Worker crash mid-job does not leave job state inconsistent.
- [ ] Duplicate retries do not emit duplicate webhooks without documented reason.
- [ ] Failure reasons are visible in job diagnostics.

---

## 11. Webhook Delivery Tests

- [ ] Completed jobs trigger webhooks when configured.
- [ ] Failed jobs trigger webhooks if that behavior is in scope.
- [ ] Webhook payload contains job ID, document ID, status, and result reference as documented.
- [ ] Webhook delivery uses signing/verification where required.
- [ ] Non-2xx webhook responses are retried with backoff.
- [ ] Webhook retries are bounded and observable.
- [ ] Duplicate webhook delivery behavior is documented and idempotent.
- [ ] Webhook timeout handling is verified.

---

## 12. Dashboard / Operator Visibility Tests

- [ ] Dashboard shows queued, running, completed, and failed job counts.
- [ ] Dashboard shows per-job status and stage progression.
- [ ] Dashboard displays OCR/classification model versions used.
- [ ] Dashboard displays failure reasons or diagnostics for failed jobs.
- [ ] Dashboard shows throughput metrics over time.
- [ ] Dashboard shows latency metrics by stage.
- [ ] Dashboard access is protected appropriately.

---

## 13. Observability and Metrics Tests

- [ ] Request metrics are emitted for public APIs.
- [ ] Queue depth / workflow backlog metrics are emitted.
- [ ] Worker success/failure/retry counters are emitted.
- [ ] OCR latency metrics are emitted.
- [ ] Classification latency metrics are emitted.
- [ ] End-to-end job duration metrics are emitted.
- [ ] Failed job counts are emitted.
- [ ] Metrics labels do not create unbounded cardinality.
- [ ] Structured logs include correlation/job IDs.
- [ ] Distributed tracing spans are emitted across API, workers, and inference services.
- [ ] Alerts exist for high failure rate, high latency, queue backlog, and unavailable inference services.

---

## 14. Performance and Load Tests

- [ ] System meets documented throughput target for normal load.
- [ ] System meets documented p95/p99 latency targets for asynchronous completion time where defined.
- [ ] Queue backlog drains within acceptable time under expected peak load.
- [ ] OCR services scale under concurrent page-processing load.
- [ ] Classification services scale under concurrent document-processing load.
- [ ] Autoscaling behavior is validated if autoscaling is in scope.
- [ ] Large-batch ingestion does not cause cascading failure.
- [ ] Resource limits and requests are tuned to avoid noisy-neighbor issues.

---

## 15. Accuracy and Quality Gates

- [ ] A representative evaluation dataset exists for supported document classes.
- [ ] OCR quality is measured on representative samples.
- [ ] Classification accuracy/F1 is measured on representative samples.
- [ ] Minimum acceptable OCR and classification quality thresholds are defined.
- [ ] Quality thresholds are met for the target release.
- [ ] Confusion matrix or class-level performance is reviewed for major classes.
- [ ] Low-confidence and misclassification handling is documented.
- [ ] Model evaluation results are tied to specific model versions.

---

## 16. Model Versioning and Deployment Tests

- [ ] Each deployed OCR model has an explicit version identifier.
- [ ] Each deployed classification model has an explicit version identifier.
- [ ] Active model version can be inspected through config, DB, or deployment metadata.
- [ ] New model versions can be deployed without taking the platform offline.
- [ ] Canary, blue/green, or equivalent rollout flow is tested.
- [ ] Rollback to a previous model version is tested.
- [ ] Jobs processed during rollout remain traceable to the correct model version.
- [ ] Mixed-version traffic during rollout behaves as expected.
- [ ] Model artifact provenance is documented.

---

## 17. Security and Compliance Readiness

- [ ] All service-to-service traffic is protected according to policy.
- [ ] Access to object storage and database is least-privilege.
- [ ] Authentication tokens/keys are rotated and stored securely.
- [ ] Sensitive document content is protected at rest and in transit.
- [ ] Audit logging exists for relevant administrative actions.
- [ ] Data deletion or redaction flow exists if required by scope.
- [ ] Third-party/open-source licenses are reviewed for included components.

---

## 18. Deployment and Infrastructure Tests

- [ ] Infrastructure can be provisioned from code.
- [ ] Local development environment can run a representative subset of the system.
- [ ] CI builds all services successfully.
- [ ] CI runs unit/integration tests automatically.
- [ ] CD deploys services reproducibly.
- [ ] Health/readiness probes are configured for all deployable services.
- [ ] Rolling deployments do not interrupt in-flight traffic beyond documented limits.
- [ ] Disaster recovery assumptions are documented and at least minimally tested.

---

## 19. Testing Pyramid Completeness

### Unit Tests
- [ ] API request validation logic has unit tests.
- [ ] Job state transition logic has unit tests.
- [ ] Queue/workflow utility logic has unit tests.
- [ ] Storage adapter logic has unit tests.
- [ ] Webhook signing/verification logic has unit tests.
- [ ] Inference client wrappers have unit tests.

### Integration Tests
- [ ] API + DB integration tests exist.
- [ ] API + object storage integration tests exist.
- [ ] Worker + queue/workflow integration tests exist.
- [ ] Worker + OCR service integration tests exist.
- [ ] Worker + classification service integration tests exist.
- [ ] Webhook delivery integration tests exist.

### End-to-End Tests
- [ ] At least one happy-path PDF end-to-end test exists.
- [ ] At least one happy-path image end-to-end test exists.
- [ ] At least one failure-path end-to-end test exists.
- [ ] At least one retry-path end-to-end test exists.
- [ ] At least one model-rollout or model-version traceability test exists.

---

## 20. Documentation Completion

- [ ] README explains architecture, setup, and main workflows.
- [ ] API documentation is complete and current.
- [ ] Deployment documentation is complete and current.
- [ ] Runbook exists for common operational failures.
- [ ] Model deployment/versioning process is documented.
- [ ] Observability dashboards and alert meanings are documented.
- [ ] Supported and unsupported document scenarios are documented.
- [ ] Known limitations are documented.

---

## 21. Final Release Gate

The platform is only considered done when all of the following are true:

- [ ] All critical and high-priority checklist items are complete.
- [ ] No known Sev-1 or Sev-2 defects remain open.
- [ ] Automated test suite passes in CI.
- [ ] End-to-end acceptance tests pass on a release candidate.
- [ ] Observability dashboards and alerts are live.
- [ ] Model versioning and rollback have been demonstrated.
- [ ] Security review items in scope are complete.
- [ ] Documentation is complete enough for handoff and operation.
- [ ] The team can process representative real documents from upload to final result without manual intervention outside defined review paths.

---

## 22. Optional “Excellent, Not Just Done” Items

- [ ] Manual review queue exists for low-confidence documents.
- [ ] Reprocessing jobs can be triggered against a new model version.
- [ ] Per-tenant quotas and rate limits are supported.
- [ ] Search over extracted text is supported.
- [ ] Cost-per-document metrics are tracked.
- [ ] SLA/SLO dashboards are defined and monitored.
- [ ] Shadow testing exists for candidate model versions.
- [ ] Benchmark suite exists for regression detection across model and platform changes.

