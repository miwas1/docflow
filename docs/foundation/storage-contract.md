# Foundation Storage Contract

The Phase 1 platform uses a single object-storage namespace and a single Postgres metadata database.

## Object Storage Namespace

Object storage stores blobs using the canonical pattern `tenants/{tenant_id}/jobs/{job_id}/{stage}/{artifact_type}/{filename}`.

Supported Phase 1 artifact type tokens:

- `original`
- `page-image`
- `ocr-json`
- `extracted-text`
- `classification-result`

## Storage Responsibilities

Postgres stores metadata for:

- jobs and their current state
- job lifecycle events
- artifact descriptors and object-storage keys
- model family / version rollout metadata

Object storage stores blobs for:

- the original uploaded file
- derived page images
- per-page OCR JSON
- aggregated extracted text
- classification result payloads

## Later Phase Expectations

- Digital extraction outputs and OCR outputs must both land under the same `stage` and `artifact_type` namespace so downstream consumers do not need separate lookup rules.
- API and worker flows should persist object-storage keys in Postgres rather than embedding object payloads in relational tables.
- Services may evolve their internal processing, but they should not silently change the canonical object key layout established in Phase 1.
