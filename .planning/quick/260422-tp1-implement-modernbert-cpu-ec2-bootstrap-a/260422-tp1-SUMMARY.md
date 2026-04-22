# Quick Task 260422-tp1 Summary

- Replaced the classifier keyword baseline with a ModernBERT-backed similarity runtime that keeps the existing HTTP contract and low-confidence fallback behavior.
- Added classifier runtime settings for model identity, cache location, CPU device selection, and label-description prototypes.
- Added `scripts/bootstrap_ec2_dev.sh` to install Docker when needed, create `.env`, create the host cache, and pre-download the configured ModernBERT snapshot.
- Wired `docker-compose.yml` to use `.env`, mount the host Hugging Face cache into the classifier container, and pass explicit model runtime env vars.
- Updated `README.md` with the new local and EC2 setup flow, including the one-time bootstrap step and recommended EC2 instance sizes.
- Added focused classifier tests for runtime behavior and configuration parsing.
