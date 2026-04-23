# Quick Task Summary (260422-wln)

## Goal

Add a script that generates the `raw.jsonl` training input by extracting text from local documents via the running extractor service, using folder names as labels.

## Delivered

- `training/text_finetune/scripts/generate_raw_jsonl.py`
  - supports label inference from `input-dir/<label>/<file>`
  - calls `EXTRACTOR_BASE_URL` (defaults to `http://localhost:8001`)
  - writes JSONL rows containing `id`, `label`, `text`, and extraction metadata
- Updated `training/text_finetune/README.md` with a generator-based workflow.

## Verification

- `python3 -m py_compile training/text_finetune/scripts/generate_raw_jsonl.py`

