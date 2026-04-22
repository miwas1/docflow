# ModernBERT EC2 Dev Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a CPU-friendly ModernBERT-backed classifier runtime plus a one-time EC2 bootstrap flow that pre-downloads the model and keeps daily development on `docker compose up --build`.

**Architecture:** The classifier service will load a ModernBERT encoder from a mounted Hugging Face cache and classify extracted text by cosine similarity against fixed taxonomy prototypes. A one-time bootstrap script will install Docker on EC2, create the cache directory, seed `.env`, and download the configured model before any containers start. Compose, env defaults, and README will be updated so the workflow stays consistent locally and on EC2.

**Tech Stack:** Python, FastAPI, PyTorch, Transformers, Hugging Face Hub, Docker Compose, bash

---

### Task 1: Add failing tests for the ModernBERT runtime and bootstrap configuration

**Files:**
- Modify: `services/classifier/tests/test_inference_service.py`
- Create: `services/classifier/tests/test_bootstrap_config.py`

- [ ] **Step 1: Write failing classifier tests**

Add tests for:
- a model-backed invoice classification path using a fake embedder
- low-confidence fallback to `unknown_other`
- settings-driven trace metadata

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/classifier/src pytest services/classifier/tests/test_inference_service.py services/classifier/tests/test_bootstrap_config.py -q`
Expected: FAIL because the ModernBERT settings, bootstrap helpers, and embedder-backed inference path do not exist yet.

- [ ] **Step 3: Commit planning checkpoint**

```bash
git add docs/superpowers/plans/2026-04-22-modernbert-ec2-dev-setup-plan.md
git commit -m "docs: add ModernBERT EC2 setup implementation plan"
```

### Task 2: Implement the classifier runtime and configuration

**Files:**
- Modify: `services/classifier/src/classifier_service/config.py`
- Modify: `services/classifier/src/classifier_service/inference.py`
- Modify: `services/classifier/src/classifier_service/main.py`
- Modify: `services/classifier/pyproject.toml`
- Modify: `services/classifier/Dockerfile`
- Modify: `.env.example`

- [ ] **Step 1: Add runtime dependencies and settings**

Add `torch`, `transformers`, and `huggingface_hub`, plus settings for model ID, provider, cache path, device, and prototype labels.

- [ ] **Step 2: Implement a load-on-start classifier runtime**

Create a model loader that:
- loads tokenizer and encoder from local cache
- precomputes taxonomy prototype embeddings
- performs cosine-similarity scoring for requests
- preserves the existing response contract and confidence threshold behavior

- [ ] **Step 3: Run targeted classifier tests**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/classifier/src pytest services/classifier/tests/test_health.py services/classifier/tests/test_inference_service.py services/classifier/tests/test_bootstrap_config.py -q`
Expected: PASS.

### Task 3: Implement the EC2 bootstrap flow and docs

**Files:**
- Create: `scripts/bootstrap_ec2_dev.sh`
- Modify: `docker-compose.yml`
- Modify: `README.md`

- [ ] **Step 1: Add the bootstrap script**

Implement an idempotent script that:
- installs Docker on Amazon Linux 2023
- enables and starts Docker
- adds the chosen user to the Docker group
- creates `/opt/doc-platform/hf-cache`
- creates `.env` from `.env.example` when absent
- downloads the configured ModernBERT snapshot into the cache

- [ ] **Step 2: Wire compose to the host cache**

Update `classifier` service config so it mounts the cache and receives the model/device env vars.

- [ ] **Step 3: Update local and EC2 setup docs**

Document:
- the one-time bootstrap command
- recommended EC2 sizes
- the mounted model cache path
- how normal compose rebuilds use the latest repo code without redownloading the model

- [ ] **Step 4: Run focused verification**

Run:
- `bash -n scripts/bootstrap_ec2_dev.sh`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=packages/contracts/src:services/classifier/src pytest services/classifier/tests/test_health.py services/classifier/tests/test_inference_service.py services/classifier/tests/test_bootstrap_config.py -q`

Expected: both commands succeed.

