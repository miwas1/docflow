#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def _read_labels(data_dir: Path, labels_json: str | None) -> list[str]:
    if labels_json:
        labels = json.loads(labels_json)
        if not isinstance(labels, list) or not all(isinstance(x, str) for x in labels):
            raise SystemExit("--labels-json must be a JSON array of strings")
        return labels
    labels_path = data_dir / "labels.json"
    if not labels_path.exists():
        raise SystemExit("Missing labels.json. Run prepare_dataset.py first or pass --labels-json.")
    return json.loads(labels_path.read_text(encoding="utf-8"))


def _tokenize_dataset(dataset, tokenizer, *, max_length: int, stride: int) -> object:
    # When stride > 0 we enable sliding-window chunking so long documents are split
    # into multiple training examples.
    def tokenize_batch(batch):
        enc = tokenizer(
            batch["text"],
            truncation=True,
            max_length=max_length,
            padding=False,
            return_overflowing_tokens=(stride > 0),
            stride=stride if stride > 0 else 0,
        )
        if "overflow_to_sample_mapping" not in enc:
            enc["labels"] = batch["label_id"]
            return enc

        # Map overflowed chunks back to original label IDs.
        mapping = enc["overflow_to_sample_mapping"]
        enc["labels"] = [batch["label_id"][idx] for idx in mapping]
        return enc

    remove_cols = [c for c in dataset.column_names if c not in ("text", "label_id")]
    return dataset.map(tokenize_batch, batched=True, remove_columns=remove_cols)


def main() -> None:
    ap = argparse.ArgumentParser(description="Fine-tune a text classifier on extracted text (ModernBERT).")
    ap.add_argument("--data-dir", required=True, help="Directory containing train/val/test JSONL + labels.json.")
    ap.add_argument("--output-dir", required=True, help="Where to write run artifacts (model, logs, metrics).")
    ap.add_argument("--base-model", default=os.environ.get("CLASSIFIER_MODEL_NAME", "answerdotai/ModernBERT-base"))
    ap.add_argument("--cache-dir", default=os.environ.get("HF_HOME") or os.environ.get("TRANSFORMERS_CACHE"))
    ap.add_argument("--labels-json", default=None, help="Optional JSON array of labels (overrides labels.json).")
    ap.add_argument("--max-length", type=int, default=512)
    ap.add_argument("--stride", type=int, default=0, help="If >0, chunk long docs with overlap stride.")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--train-batch-size", type=int, default=8)
    ap.add_argument("--eval-batch-size", type=int, default=16)
    ap.add_argument("--seed", type=int, default=1337)
    args = ap.parse_args()

    from datasets import load_dataset
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, DataCollatorWithPadding, Trainer, TrainingArguments

    data_dir = Path(args.data_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    labels = _read_labels(data_dir, args.labels_json)
    label2id = {label: i for i, label in enumerate(labels)}
    id2label = {i: label for label, i in label2id.items()}

    ds = load_dataset(
        "json",
        data_files={
            "train": str(data_dir / "train.jsonl"),
            "validation": str(data_dir / "val.jsonl"),
            "test": str(data_dir / "test.jsonl"),
        },
    )

    def add_label_id(batch):
        return {"label_id": [label2id[label] for label in batch["label"]]}

    ds = ds.map(add_label_id, batched=True)

    tokenizer = AutoTokenizer.from_pretrained(
        args.base_model,
        cache_dir=args.cache_dir,
        local_files_only=True if args.cache_dir else False,
        use_fast=True,
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        args.base_model,
        cache_dir=args.cache_dir,
        local_files_only=True if args.cache_dir else False,
        num_labels=len(labels),
        id2label=id2label,
        label2id=label2id,
    )

    tokenized_train = _tokenize_dataset(ds["train"], tokenizer, max_length=args.max_length, stride=args.stride)
    tokenized_val = _tokenize_dataset(ds["validation"], tokenizer, max_length=args.max_length, stride=args.stride)

    collator = DataCollatorWithPadding(tokenizer=tokenizer)

    training_args = TrainingArguments(
        output_dir=str(out_dir / "hf_trainer"),
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        per_device_train_batch_size=args.train_batch_size,
        per_device_eval_batch_size=args.eval_batch_size,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        logging_strategy="steps",
        logging_steps=25,
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        seed=args.seed,
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train,
        eval_dataset=tokenized_val,
        tokenizer=tokenizer,
        data_collator=collator,
    )

    trainer.train()

    model_dir = out_dir / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    trainer.model.save_pretrained(str(model_dir))
    tokenizer.save_pretrained(str(model_dir))

    run_meta = {
        "base_model": args.base_model,
        "labels": labels,
        "max_length": args.max_length,
        "stride": args.stride,
        "epochs": args.epochs,
        "lr": args.lr,
        "train_batch_size": args.train_batch_size,
        "eval_batch_size": args.eval_batch_size,
        "seed": args.seed,
    }
    (out_dir / "run.json").write_text(json.dumps(run_meta, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote fine-tuned model to: {model_dir}")


if __name__ == "__main__":
    main()

