# ModernBERT EC2 Dev Setup Design

**Date:** 2026-04-22
**Status:** Proposed
**Scope:** CPU-only EC2 development setup for the classifier service using a one-time bootstrap script plus normal `docker compose up --build` runs.

## Goal

Make ModernBERT-based classification easy to develop on an EC2 instance without turning daily development into a custom deployment workflow. After one setup script runs, regular repo-driven compose commands should rebuild the current code while reusing a persistent downloaded model cache.

## Design Summary

The development flow stays centered on the existing Docker Compose stack. We add a one-time EC2 bootstrap script that installs host prerequisites, prepares persistent directories, creates a `.env` file if needed, and downloads the selected ModernBERT model into a host cache directory before any containers start.

The classifier service remains the only component that knows about the model runtime. Docker Compose mounts the host cache into the classifier container and passes explicit runtime configuration through environment variables. That keeps the API, orchestrator, and extractor unchanged except for the classifier contract they already call.

## Recommended Approach

### Option A: One-time host bootstrap plus persistent model cache

This is the recommended approach.

- Add a repo script such as `scripts/bootstrap_ec2_dev.sh`.
- The script installs Docker and compose prerequisites on Amazon Linux 2023.
- It creates a persistent cache directory such as `/opt/doc-platform/hf-cache`.
- It downloads the configured ModernBERT snapshot during setup, not at first request.
- The classifier container reads from the mounted host cache and runs CPU inference by default.

**Why this is the best fit**

- Matches the user request for a setup script that runs once.
- Keeps `docker compose up --build` as the normal developer loop.
- Avoids first-run latency and surprise outbound downloads during service startup.
- Preserves a clean path to production-grade hosting later.

### Option B: Lazy model download on first classifier container start

- Simpler initial bootstrap script.
- More fragile developer experience because first boot depends on network availability and can be slow or opaque.

### Option C: Bake the model into the classifier image

- Predictable startup once built.
- Poor fit for active development because image builds become large and slow, and model upgrades force image rebuilds every time.

## Architecture

### Host setup

The EC2 host is responsible for durable prerequisites only:

- Docker engine installation
- Docker group membership for the chosen user
- persistent model cache directory
- optional persistent project root directory
- first-run environment file creation

The host is not responsible for running Python services directly. Application execution remains containerized.

### Classifier runtime

The classifier service gains explicit runtime configuration for:

- Hugging Face model identifier
- cache path inside the container
- host cache mount path
- CPU device selection
- optional max input length and batch size tuning

At startup, the classifier loads the tokenizer and model from the mounted cache. If the cache does not contain the configured snapshot, startup should fail with a clear error rather than silently downloading another copy.

### Compose integration

`docker-compose.yml` should mount the host cache only into the classifier service. The compose file should also pass:

- `CLASSIFIER_MODEL_NAME`
- `CLASSIFIER_MODEL_VERSION`
- `CLASSIFIER_MODEL_PROVIDER`
- `HF_HOME` or `TRANSFORMERS_CACHE`
- `TORCH_DEVICE=cpu`

This keeps the model-specific concerns isolated to the classifier boundary.

## Components

### `scripts/bootstrap_ec2_dev.sh`

Responsibilities:

- verify the script is running on a supported Linux environment
- install Docker if missing
- enable and start Docker
- add the target user to the Docker group
- create `/opt/doc-platform/hf-cache`
- optionally create `/opt/doc-platform/runtime`
- create `.env` from `.env.example` if `.env` is absent
- pre-download the ModernBERT model snapshot into the host cache
- print exact next steps for starting the stack

The script should be idempotent so it can be re-run safely when dependencies drift.

### `services/classifier`

Responsibilities:

- add `transformers`, `torch`, and any minimal supporting inference dependencies
- replace the current keyword baseline with a model-loading inference path behind the existing service boundary
- preserve current response shape, confidence thresholding, and `unknown_other` fallback semantics
- expose startup failures clearly when the expected model cache is missing or unreadable

### `docker-compose.yml`

Responsibilities:

- mount the host cache directory into the classifier container
- pass classifier model env vars
- keep the rest of the stack unchanged unless the classifier needs a healthcheck grace period increase for model load time

### `.env.example`

Responsibilities:

- document the default ModernBERT model identifier
- document the CPU-default runtime knobs
- document the host cache path expected by the bootstrap flow

### `README.md`

Responsibilities:

- document the one-time EC2 bootstrap flow
- document where the model is cached
- document how repeated compose runs reuse the cached model while rebuilding the latest code
- document the minimum EC2 shape recommended for CPU dev

## Data Flow

### One-time setup flow

1. Developer clones the repo onto EC2.
2. Developer runs `scripts/bootstrap_ec2_dev.sh`.
3. The script installs Docker and creates the model cache directory.
4. The script downloads the configured ModernBERT model into the cache.
5. The script ensures `.env` exists and points to the intended classifier settings.

### Daily development flow

1. Developer pulls or edits current repo code.
2. Developer runs `docker compose up --build`.
3. Docker rebuilds the classifier image from current source code.
4. The classifier container mounts the pre-populated host cache.
5. The classifier starts without re-downloading the model.

### Classification flow

1. Extractor and orchestrator continue producing normalized extracted text.
2. Classifier loads ModernBERT tokenizer and model from the mounted cache.
3. Incoming extracted text is tokenized and scored against the fixed taxonomy.
4. The service returns the same contract shape already used downstream.
5. Threshold logic still maps low-confidence predictions to `unknown_other`.

## Operational Decisions

### CPU-only development target

The development target is CPU-only EC2. This keeps setup cost low and avoids introducing CUDA, NVIDIA runtime configuration, or GPU-only docker dependencies during early classifier iteration.

Recommended baseline for dev:

- at least 4 vCPU
- at least 16 GB RAM
- 30 GB or more of free disk to leave room for Docker layers, model cache, and artifacts

### Model download timing

The model should download during bootstrap, not container startup. This makes failures happen earlier and in a place where the user can rerun setup intentionally.

### Cache ownership

The host owns the persistent cache. Containers treat it as mounted runtime data, not image contents.

## Error Handling

- If Docker installation fails, the bootstrap script should exit non-zero with the failing command surfaced clearly.
- If the model download fails, the script should stop and report the exact model identifier that failed.
- If the cache directory exists but is unreadable by Docker, the classifier should fail fast on startup with a clear filesystem error.
- If the configured model name in `.env` does not match the downloaded snapshot, classifier startup should fail rather than silently pulling another version.
- If EC2 is too small for acceptable CPU inference, the README should call out expected latency trade-offs rather than pretending the setup is production-like.

## Testing Strategy

### Bootstrap validation

- smoke-test the script on a fresh Amazon Linux 2023 instance
- re-run the script to confirm idempotency
- verify that the cache directory contains the expected Hugging Face snapshot after setup

### Service validation

- add classifier tests for model-loader initialization and configuration parsing
- add at least one inference test that exercises the ModernBERT-backed path behind the current HTTP endpoint
- keep the existing contract tests intact so the orchestrator and API do not need schema changes

### Compose validation

- verify `docker compose up --build classifier` starts successfully using the mounted cache
- verify a second compose run does not re-download the model

## Out of Scope

- GPU inference
- production autoscaling
- baking the model into Docker images
- adding layout-aware or image-aware classification in this step
- changing the external classification API contract

## Open Questions Resolved

- **Setup mode:** one-time bootstrap script, not cloud-init
- **Hardware target:** CPU-only EC2 dev
- **Model download timing:** pre-download during setup, not lazy at runtime

## Implementation Handoff

Implementation should follow a small, staged plan:

1. Add classifier runtime dependencies and config knobs.
2. Add the bootstrap script and cache download logic.
3. Wire compose mounts and env vars.
4. Update the README with the new EC2 development path.
5. Add focused tests for config, startup, and inference behavior.
