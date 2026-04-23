#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(description="Export a fine-tuned model directory for deployment.")
    ap.add_argument("--model-dir", required=True, help="Directory created by train.py (contains config.json, weights, tokenizer files).")
    ap.add_argument("--export-dir", required=True, help="Destination directory for deployment artifacts.")
    args = ap.parse_args()

    model_dir = Path(args.model_dir)
    export_dir = Path(args.export_dir)
    if not model_dir.exists():
        raise SystemExit(f"Missing model-dir: {model_dir}")

    if export_dir.exists():
        shutil.rmtree(export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)

    for name in model_dir.iterdir():
        if name.is_dir():
            shutil.copytree(name, export_dir / name.name)
        else:
            shutil.copy2(name, export_dir / name.name)

    meta = {
        "exported_from": str(model_dir),
        "export_dir": str(export_dir),
        "notes": [
            "This is a standard Hugging Face model directory.",
            "In deployment, set CLASSIFIER_MODEL_NAME to this directory path inside the container, "
            "or mount it and point from_pretrained(...) to it.",
        ],
    }
    (export_dir / "EXPORT_METADATA.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    print(f"Exported model to: {export_dir}")


if __name__ == "__main__":
    main()

