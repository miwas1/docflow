#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(description="Evaluate a fine-tuned text classifier on the test split.")
    ap.add_argument("--data-dir", required=True, help="Directory containing test.jsonl and labels.json.")
    ap.add_argument("--model-dir", required=True, help="Path to saved model directory (from train.py).")
    ap.add_argument("--max-length", type=int, default=512)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--out-dir", default=None, help="Optional directory to write metrics artifacts.")
    args = ap.parse_args()

    import numpy as np
    from datasets import load_dataset
    from sklearn.metrics import classification_report, confusion_matrix
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    import torch

    data_dir = Path(args.data_dir)
    model_dir = Path(args.model_dir)
    out_dir = Path(args.out_dir) if args.out_dir else (model_dir.parent / "eval")
    out_dir.mkdir(parents=True, exist_ok=True)

    labels = json.loads((data_dir / "labels.json").read_text(encoding="utf-8"))
    label2id = {label: i for i, label in enumerate(labels)}

    ds = load_dataset("json", data_files={"test": str(data_dir / "test.jsonl")})["test"]
    y_true = [label2id[row["label"]] for row in ds]

    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
    model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)

    y_pred: list[int] = []

    def batch_iter(items, batch_size: int):
        for i in range(0, len(items), batch_size):
            yield items[i : i + batch_size]

    with torch.no_grad():
        for batch in batch_iter(ds["text"], args.batch_size):
            enc = tokenizer(
                batch,
                truncation=True,
                max_length=args.max_length,
                padding=True,
                return_tensors="pt",
            )
            enc = {k: v.to(device) for k, v in enc.items()}
            logits = model(**enc).logits
            preds = logits.argmax(dim=-1).cpu().tolist()
            y_pred.extend(preds)

    report = classification_report(y_true, y_pred, target_names=labels, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(labels))))

    (out_dir / "classification_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (out_dir / "confusion_matrix.json").write_text(json.dumps(cm.tolist(), indent=2) + "\n", encoding="utf-8")

    # Also write a CSV for easy spreadsheet viewing.
    csv_lines = ["," + ",".join(labels)]
    for i, row in enumerate(cm.tolist()):
        csv_lines.append(labels[i] + "," + ",".join(str(x) for x in row))
    (out_dir / "confusion_matrix.csv").write_text("\n".join(csv_lines) + "\n", encoding="utf-8")

    macro_f1 = float(report["macro avg"]["f1-score"])
    weighted_f1 = float(report["weighted avg"]["f1-score"])
    summary = {"macro_f1": macro_f1, "weighted_f1": weighted_f1, "n_test": len(y_true), "labels": labels}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

