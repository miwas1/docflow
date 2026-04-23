"""Fine-tuned document classification helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
import math
import re

from pydantic import BaseModel

from doc_platform_contracts.classification import (
    ClassificationCandidate,
    ClassifierTrace,
    DocumentClassificationResult,
)

from classifier_service.config import ClassifierSettings, get_settings


class ClassificationRequest(BaseModel):
    job_id: str
    document_id: str
    tenant_id: str
    source_media_type: str
    text: str
    source_artifact_ids: list[str]


class ClassificationError(Exception):
    def __init__(self, *, error_code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status_code = status_code


def _softmax(scores: list[float]) -> list[float]:
    # Lightweight fallback for tests; production uses torch.softmax.
    import math

    if not scores:
        return []
    max_score = max(scores)
    exps = [math.exp(score - max_score) for score in scores]
    total = sum(exps) or 1.0
    return [value / total for value in exps]


class SequenceClassifierRuntime:
    def __init__(
        self,
        settings: ClassifierSettings,
        *,
        torch_module=None,
        tokenizer=None,
        model=None,
    ) -> None:
        self.settings = settings

        if torch_module is None or tokenizer is None or model is None:
            try:
                import torch
                from transformers import AutoModelForSequenceClassification
                from transformers import AutoTokenizer
            except ImportError as exc:
                raise RuntimeError(
                    "Fine-tuned classifier runtime dependencies are not installed. "
                    "Install classifier extras before starting the service."
                ) from exc

            torch_module = torch
            tokenizer = AutoTokenizer.from_pretrained(
                settings.classifier_model_name,
                cache_dir=settings.classifier_model_cache_dir,
                local_files_only=settings.classifier_model_local_files_only,
            )
            model = AutoModelForSequenceClassification.from_pretrained(
                settings.classifier_model_name,
                cache_dir=settings.classifier_model_cache_dir,
                local_files_only=settings.classifier_model_local_files_only,
            )

        self._torch = torch_module
        self._tokenizer = tokenizer
        self._model = model
        self._model.eval()
        self._device = settings.classifier_device
        self._model.to(self._device)
        self._max_length = settings.classifier_max_length
        self._id2label = self._load_id2label()
        self._label2id = {label: idx for idx, label in self._id2label.items()}
        self._validate_model_taxonomy()
        self._keyword_hints = _KeywordHints(
            enabled=settings.classifier_keyword_hints_enabled,
            margin=settings.classifier_keyword_hints_margin,
            boost_per_hit=settings.classifier_keyword_hints_boost,
            max_boost=settings.classifier_keyword_hints_max_boost,
            min_hits=settings.classifier_keyword_hints_min_hits,
            label2id=self._label2id,
        )

    def _load_id2label(self) -> dict[int, str]:
        mapping = getattr(self._model.config, "id2label", None)
        if isinstance(mapping, dict) and mapping:
            return {int(key): value for key, value in mapping.items()}
        raise ValueError(
            "The configured classifier model does not expose id2label metadata. "
            "Point CLASSIFIER_MODEL_NAME at a fine-tuned sequence-classification model directory."
        )

    def _validate_model_taxonomy(self) -> None:
        if not self.settings.classifier_strict_taxonomy_validation:
            return

        # Detect "base" / unconfigured heads early (common misconfiguration).
        labels = list(self._id2label.values())
        if labels and all(isinstance(label, str) and label.startswith("LABEL_") for label in labels):
            raise ValueError(
                "Classifier model id2label contains only generic LABEL_* entries. "
                "This usually means you loaded a base checkpoint instead of a fine-tuned model directory. "
                "Point CLASSIFIER_MODEL_NAME at your exported fine-tuned model."
            )

        expected = set((self.settings.classifier_label_descriptions or {}).keys())
        if not expected:
            return

        expected.discard("unknown_other")
        model_labels = set(labels)
        missing = sorted(expected - model_labels)
        if missing:
            raise ValueError(
                "Classifier model taxonomy mismatch: model is missing expected labels. "
                f"Missing: {missing}. "
                "Ensure CLASSIFIER_MODEL_NAME points at the same fine-tuned model used for this taxonomy."
            )

    def classify(self, text: str) -> list[ClassificationCandidate]:
        encoded = self._tokenizer(
            [text],
            padding=True,
            truncation=True,
            max_length=self._max_length,
            return_tensors="pt",
        )
        encoded = {key: value.to(self._device) for key, value in encoded.items()}

        with self._torch.no_grad():
            outputs = self._model(**encoded)

        logits_row = _logits_to_row(outputs.logits)
        probabilities = self._probabilities_from_scores(logits_row)

        if self._keyword_hints.enabled and len(probabilities) >= 2:
            top_two = sorted(probabilities, reverse=True)[:2]
            margin = top_two[0] - top_two[1]
            if margin < self._keyword_hints.margin:
                boosted = self._keyword_hints.apply(text, logits_row)
                if boosted is not None:
                    probabilities = self._probabilities_from_scores(boosted)

        candidates = [
            ClassificationCandidate(label=self._id2label[index], score=score)
            for index, score in enumerate(probabilities)
        ]
        candidates.sort(key=lambda candidate: candidate.score, reverse=True)
        return candidates

    def _probabilities_from_scores(self, scores: list[float]) -> list[float]:
        problem_type = getattr(getattr(self._model, "config", None), "problem_type", None)
        if problem_type == "multi_label_classification":
            return [_sigmoid(score) for score in scores]
        return _softmax(scores)


@lru_cache(maxsize=1)
def get_runtime() -> SequenceClassifierRuntime:
    return SequenceClassifierRuntime(get_settings())


def warm_runtime() -> SequenceClassifierRuntime:
    return get_runtime()


def run_classification(
    request: ClassificationRequest | dict,
    settings: ClassifierSettings | None = None,
    runtime: SequenceClassifierRuntime | None = None,
) -> DocumentClassificationResult:
    parsed_request = request if isinstance(request, ClassificationRequest) else ClassificationRequest.model_validate(request)
    settings = settings or get_settings()
    runtime = runtime or (get_runtime() if settings is get_settings() else SequenceClassifierRuntime(settings))

    matched_candidates = runtime.classify(parsed_request.text)
    if not matched_candidates:
        matched_candidates = [ClassificationCandidate(label="unknown_other", score=0.0)]

    best_candidate = matched_candidates[0]
    final_label = best_candidate.label
    if best_candidate.score < settings.classifier_confidence_threshold:
        final_label = "unknown_other"

    return DocumentClassificationResult(
        job_id=parsed_request.job_id,
        document_id=parsed_request.document_id,
        tenant_id=parsed_request.tenant_id,
        final_label=final_label,
        confidence=best_candidate.score,
        candidate_labels=matched_candidates,
        low_confidence_policy="threshold_to_unknown_other",
        threshold_applied=settings.classifier_confidence_threshold,
        produced_by=ClassifierTrace(
            provider=settings.classifier_model_provider,
            model=settings.classifier_model_name,
            version=settings.classifier_model_version,
        ),
        created_at=datetime.now(UTC),
    )


def _sigmoid(value: float) -> float:
    # Keep this numerically stable for very large magnitudes.
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def _logits_to_row(logits) -> list[float]:
    """Convert model outputs.logits into a flat list[float] for a single example."""
    if logits is None:
        return []

    if hasattr(logits, "cpu") and hasattr(logits, "tolist"):
        raw = logits.cpu().tolist()
    elif hasattr(logits, "tolist"):
        raw = logits.tolist()
    else:
        raw = logits

    if isinstance(raw, list) and raw and isinstance(raw[0], list):
        return [float(x) for x in raw[0]]
    if isinstance(raw, list):
        return [float(x) for x in raw]
    raise TypeError(f"Unsupported logits type: {type(logits)!r}")


class _KeywordHints:
    def __init__(
        self,
        *,
        enabled: bool,
        margin: float,
        boost_per_hit: float,
        max_boost: float,
        min_hits: int,
        label2id: dict[str, int],
    ) -> None:
        self.enabled = enabled
        self.margin = margin
        self.boost_per_hit = boost_per_hit
        self.max_boost = max_boost
        self.min_hits = min_hits
        self._label2id = dict(label2id)

        # These are intentionally conservative: require multiple strong cues before boosting.
        self._patterns: dict[str, list[re.Pattern[str]]] = {
            "invoice": [
                re.compile(r"\binvoice\b", re.IGNORECASE),
                re.compile(r"\bbill to\b", re.IGNORECASE),
                re.compile(r"\binvoice\s*#\b", re.IGNORECASE),
                re.compile(r"\btotal (amount )?due\b", re.IGNORECASE),
                re.compile(r"\bsubtotal\b", re.IGNORECASE),
                re.compile(r"\bdue date\b", re.IGNORECASE),
                re.compile(r"\bpayment terms\b", re.IGNORECASE),
                re.compile(r"\bpo\s*#\b", re.IGNORECASE),
            ],
            "receipt": [
                re.compile(r"\breceipt\b", re.IGNORECASE),
                re.compile(r"\bcashier\b", re.IGNORECASE),
                re.compile(r"\bpayment method\b", re.IGNORECASE),
                re.compile(r"\bchange\b", re.IGNORECASE),
            ],
            "bank_statement": [
                re.compile(r"\baccount statement\b", re.IGNORECASE),
                re.compile(r"\bstatement period\b", re.IGNORECASE),
                re.compile(r"\baccount number\b", re.IGNORECASE),
                re.compile(r"\bopening balance\b", re.IGNORECASE),
                re.compile(r"\bclosing balance\b", re.IGNORECASE),
                re.compile(r"\btransaction(s)?\b", re.IGNORECASE),
            ],
            "id_card": [
                re.compile(r"\b(id(entification)?|identity)\s+card\b", re.IGNORECASE),
                re.compile(r"\bdate of birth\b", re.IGNORECASE),
                re.compile(r"\bid number\b", re.IGNORECASE),
                re.compile(r"\bexpiry date\b", re.IGNORECASE),
            ],
            "utility_bill": [
                re.compile(r"\butility bill\b", re.IGNORECASE),
                re.compile(r"\bbilling period\b", re.IGNORECASE),
                re.compile(r"\bservice address\b", re.IGNORECASE),
                re.compile(r"\bamount due\b", re.IGNORECASE),
            ],
            "contract": [
                re.compile(r"\bagreement\b", re.IGNORECASE),
                re.compile(r"\bbetween\b", re.IGNORECASE),
                re.compile(r"\beffective date\b", re.IGNORECASE),
                re.compile(r"\bterm\b", re.IGNORECASE),
                re.compile(r"\bsignature(s)?\b", re.IGNORECASE),
                re.compile(r"\bconfidentiality\b", re.IGNORECASE),
            ],
            "medical_record": [
                re.compile(r"\bmedical record\b", re.IGNORECASE),
                re.compile(r"\bpatient\b", re.IGNORECASE),
                re.compile(r"\bmrn\b", re.IGNORECASE),
                re.compile(r"\bdiagnosis\b", re.IGNORECASE),
                re.compile(r"\bprescription\b", re.IGNORECASE),
                re.compile(r"\bprovider\b", re.IGNORECASE),
            ],
            "tax_form": [
                re.compile(r"\btax\b", re.IGNORECASE),
                re.compile(r"\btaxpayer\b", re.IGNORECASE),
                re.compile(r"\btin\b", re.IGNORECASE),
                re.compile(r"\bwithholding\b", re.IGNORECASE),
                re.compile(r"\bform\s+w-?2\b", re.IGNORECASE),
                re.compile(r"\b1099\b", re.IGNORECASE),
            ],
        }

    def apply(self, text: str, logits_row: list[float]) -> list[float] | None:
        boosts = self._compute_boosts(text)
        if not boosts:
            return None
        boosted = list(logits_row)
        for idx, boost in boosts.items():
            if 0 <= idx < len(boosted):
                boosted[idx] += boost
        return boosted

    def _compute_boosts(self, text: str) -> dict[int, float]:
        if not self.enabled:
            return {}
        if not text:
            return {}

        boosts: dict[int, float] = {}
        for label, patterns in self._patterns.items():
            idx = self._label2id.get(label)
            if idx is None:
                continue
            hits = 0
            for pat in patterns:
                if pat.search(text):
                    hits += 1
            if hits < self.min_hits:
                continue
            boost = min(self.max_boost, hits * self.boost_per_hit)
            if boost > 0:
                boosts[idx] = boost
        return boosts
