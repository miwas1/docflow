# Quick Task Summary (260423-fcl)

Implemented two guardrails in the classifier service to reduce obvious mislabels after fine-tuning:

- Strict taxonomy validation (default on): if `CLASSIFIER_LABEL_DESCRIPTIONS_JSON` is set and the loaded model does not contain those labels, the classifier fails fast instead of silently serving incorrect mappings.
- Conservative keyword hint tie-breaker (default on): when the model’s top-1 vs top-2 probability margin is small, apply small logit boosts for strong document-type cues (e.g., `invoice`, `bill to`, `total due`) to break ties.

Docs:
- Updated `README.md` troubleshooting guidance for common “fine-tuning not working” misconfigurations.

