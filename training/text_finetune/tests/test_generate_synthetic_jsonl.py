from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "training" / "text_finetune" / "scripts" / "generate_synthetic_jsonl.py"
PREPARE_SCRIPT_PATH = REPO_ROOT / "training" / "text_finetune" / "scripts" / "prepare_dataset.py"

EXPECTED_LABELS = {
    "invoice",
    "receipt",
    "bank_statement",
    "id_card",
    "utility_bill",
    "contract",
    "medical_record",
    "tax_form",
    "unknown_other",
}


def test_generate_synthetic_jsonl_writes_balanced_rows(tmp_path: Path) -> None:
    out_path = tmp_path / "raw.jsonl"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--out",
            str(out_path),
            "--examples-per-label",
            "3",
            "--seed",
            "7",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr
    assert out_path.exists()

    rows = [json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == len(EXPECTED_LABELS) * 3

    labels = [row["label"] for row in rows]
    assert set(labels) == EXPECTED_LABELS
    for label in EXPECTED_LABELS:
        assert labels.count(label) == 3

    ids = {row["id"] for row in rows}
    assert len(ids) == len(rows)

    for row in rows:
        assert isinstance(row["text"], str)
        assert row["text"].strip()


def test_generate_synthetic_jsonl_output_is_accepted_by_prepare_dataset(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.jsonl"
    processed_dir = tmp_path / "processed"

    generate = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--out",
            str(raw_path),
            "--examples-per-label",
            "2",
            "--seed",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert generate.returncode == 0, generate.stderr

    prepare = subprocess.run(
        [
            sys.executable,
            str(PREPARE_SCRIPT_PATH),
            "--input",
            str(raw_path),
            "--out-dir",
            str(processed_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )

    assert prepare.returncode == 0, prepare.stderr
    assert (processed_dir / "train.jsonl").exists()
    assert (processed_dir / "val.jsonl").exists()
    assert (processed_dir / "test.jsonl").exists()
    assert (processed_dir / "labels.json").exists()
