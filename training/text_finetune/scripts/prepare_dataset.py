#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

DEFAULT_LABELS = [
    "invoice",
    "receipt",
    "bank_statement",
    "id_card",
    "utility_bill",
    "contract",
    "medical_record",
    "tax_form",
    "unknown_other",
]


@dataclass(frozen=True)
class Example:
    id: str
    label: str
    text: str
    source_media_type: str | None = None


def _load_labels(labels_json: str | None) -> list[str]:
    if not labels_json:
        return list(DEFAULT_LABELS)
    labels = json.loads(labels_json)
    if not isinstance(labels, list) or not all(isinstance(x, str) for x in labels):
        raise SystemExit("--labels-json must be a JSON array of strings")
    if "unknown_other" not in labels:
        labels.append("unknown_other")
    return labels


def _read_jsonl(path: Path, *, allowed_labels: set[str]) -> list[Example]:
    examples: list[Example] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw:
                continue
            row = json.loads(raw)
            if not isinstance(row, dict):
                raise SystemExit(f"{path}:{line_no}: JSONL row must be an object")

            label = row.get("label")
            text = row.get("text")
            if not isinstance(label, str) or not label:
                raise SystemExit(f"{path}:{line_no}: missing/invalid 'label'")
            if label not in allowed_labels:
                raise SystemExit(f"{path}:{line_no}: label '{label}' not in allowed label set")
            if not isinstance(text, str) or not text.strip():
                raise SystemExit(f"{path}:{line_no}: missing/invalid 'text'")

            ex_id = row.get("id")
            if not isinstance(ex_id, str) or not ex_id:
                ex_id = f"row-{line_no}"

            source_media_type = row.get("source_media_type")
            if source_media_type is not None and not isinstance(source_media_type, str):
                raise SystemExit(f"{path}:{line_no}: invalid 'source_media_type' (must be string)")

            examples.append(
                Example(
                    id=ex_id,
                    label=label,
                    text=text.strip(),
                    source_media_type=source_media_type,
                )
            )
    return examples


def _split_by_label(
    examples: list[Example],
    *,
    seed: int,
    train_ratio: float,
    val_ratio: float,
) -> tuple[list[Example], list[Example], list[Example]]:
    if train_ratio <= 0 or val_ratio < 0 or train_ratio + val_ratio >= 1.0:
        raise SystemExit("Invalid split ratios. Require: train_ratio>0, val_ratio>=0, train_ratio+val_ratio<1")

    rng = random.Random(seed)
    by_label: dict[str, list[Example]] = defaultdict(list)
    for ex in examples:
        by_label[ex.label].append(ex)

    train: list[Example] = []
    val: list[Example] = []
    test: list[Example] = []

    for label, group in by_label.items():
        rng.shuffle(group)
        n = len(group)
        n_train = max(1, int(round(n * train_ratio)))
        n_val = int(round(n * val_ratio))
        if n_train + n_val >= n:
            n_val = max(0, n - n_train - 1)
        train.extend(group[:n_train])
        val.extend(group[n_train : n_train + n_val])
        test.extend(group[n_train + n_val :])

    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)
    return train, val, test


def _write_jsonl(path: Path, examples: list[Example]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for ex in examples:
            row = {"id": ex.id, "label": ex.label, "text": ex.text}
            if ex.source_media_type:
                row["source_media_type"] = ex.source_media_type
            f.write(json.dumps(row, ensure_ascii=True) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Validate and split JSONL into train/val/test.")
    ap.add_argument("--input", required=True, help="Path to raw JSONL (label/text).")
    ap.add_argument("--out-dir", required=True, help="Output directory for processed splits.")
    ap.add_argument("--labels-json", default=None, help="JSON array of allowed labels.")
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--train-ratio", type=float, default=0.8)
    ap.add_argument("--val-ratio", type=float, default=0.1)
    args = ap.parse_args()

    labels = _load_labels(args.labels_json)
    allowed = set(labels)
    raw_path = Path(args.input)
    out_dir = Path(args.out_dir)

    examples = _read_jsonl(raw_path, allowed_labels=allowed)
    if not examples:
        raise SystemExit("No examples found in input.")

    train, val, test = _split_by_label(
        examples, seed=args.seed, train_ratio=args.train_ratio, val_ratio=args.val_ratio
    )

    _write_jsonl(out_dir / "train.jsonl", train)
    _write_jsonl(out_dir / "val.jsonl", val)
    _write_jsonl(out_dir / "test.jsonl", test)
    (out_dir / "labels.json").write_text(json.dumps(labels, indent=2) + "\n", encoding="utf-8")

    summary = {
        "total": len(examples),
        "train": len(train),
        "val": len(val),
        "test": len(test),
        "labels": labels,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

