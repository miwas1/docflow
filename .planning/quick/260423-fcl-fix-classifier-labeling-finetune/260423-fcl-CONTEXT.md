# Quick Task Context (260423-fcl)

User goal: fix incorrect document labels after attempting to fine-tune the ModernBERT-based classifier (example: a clear invoice being labeled `medical_record`).

Observed symptoms:
- Candidate label scores appear tightly clustered across many labels, producing unstable top-1 labels.
- Deployments can silently run with a misconfigured model/taxonomy, making results look "random" even when the pipeline is otherwise healthy.

Scope for this quick task:
- Add fast-fail taxonomy validation so misconfigured models are rejected early.
- Add a conservative keyword-based tie-breaker to reduce obvious mislabels when the model is uncertain.
- Update README local setup troubleshooting guidance.

Out of scope:
- Retraining or curating a higher-quality labeled dataset (still recommended for production accuracy).

