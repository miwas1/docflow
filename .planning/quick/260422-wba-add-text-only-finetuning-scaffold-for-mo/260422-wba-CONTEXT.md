# Quick Task Context (260422-wba)

User goal: move toward a supervised, text-only classifier that can be fine-tuned on our taxonomy using extracted text, reusing the ModernBERT base weights already downloaded by `scripts/bootstrap_ec2_dev.sh`.

Motivation:
- Similarity-based scoring yields cosine similarities (not probabilities), which can appear tightly clustered across labels.
- A supervised fine-tune provides calibrated probabilities and clearer separation when trained on representative data.

Scope for this quick task:
- Create a training scaffold folder with dataset prep, training, evaluation, and an EC2/Docker runner that reuses the HF cache.

Out of scope (for later):
- Switching `services/classifier` runtime from similarity to a sequence-classification head in production.
- Adding dataset ingestion from object storage artifacts automatically (we start with explicit JSONL input).

