# Text-Only Fine-Tuning (ModernBERT)

This folder scaffolds a **text-only** fine-tuning workflow for the platform's document classifier.

Why this exists
---------------
The current `services/classifier` runtime is a **similarity** model: it embeds the extracted text and compares it to fixed label-description prototypes. That is fast to stand up, but the scores are not probabilities and can look "close" across labels, especially when the extracted text is short/noisy.

Fine-tuning a supervised classifier produces **probabilities** over *your exact taxonomy*.

## What You Get (Matches the 5-step path)

1. Dataset prep and validation: `scripts/prepare_dataset.py`
2. Train a supervised classifier head on ModernBERT: `scripts/train.py`
3. Long document handling: optional sliding-window chunking in `scripts/train.py`
4. Evaluation and confusion matrix: `scripts/evaluate.py`
5. Export for deployment: `scripts/export_model.py`

## Data Format (JSONL)

Create a JSONL file where each line has:

```json
{"id":"doc-001","label":"invoice","text":"Invoice Number INV-42\\nTotal Due: $120.00\\nBill To: Acme Corp"}
```

Required fields:
- `label`: one of the taxonomy labels
- `text`: extracted text you want the classifier to learn from

Recommended:
- `id`: stable identifier (job_id/document_id/source file name)
- `source_media_type`: e.g. `application/pdf`, `image/png` (optional)

Example file: `training/text_finetune/data/sample_raw.jsonl`

## Labels

By default this scaffold uses the platform taxonomy:

`invoice, receipt, bank_statement, id_card, utility_bill, contract, medical_record, tax_form, unknown_other`

You can override labels via `--labels-json`.

## One Path: Start To Finish

Use this exact flow when starting from zero data. It generates synthetic post-extraction
text, prepares train/validation/test splits, fine-tunes ModernBERT, evaluates the run,
and exports the final model directory.

### Step 0: Install training dependencies

```bash
python3 -m pip install -r training/text_finetune/requirements.txt
```

### Step 1: Generate `raw.jsonl`

The classifier consumes extracted text after the OCR/extraction stage, so the canonical
bootstrap path is to generate synthetic text that looks like post-extraction content.

```bash
python3 training/text_finetune/scripts/generate_synthetic_jsonl.py \
  --out training/text_finetune/data/raw.synthetic.jsonl \
  --examples-per-label 250 \
  --seed 42
```

This writes labeled rows for:

- `invoice`
- `receipt`
- `bank_statement`
- `id_card`
- `utility_bill`
- `contract`
- `medical_record`
- `tax_form`
- `unknown_other`

By default the script adds light OCR-style noise so the model sees slightly imperfect text.
If you want cleaner text for an experiment, add `--disable-ocr-noise`.

### Step 2: Prepare splits

This validates the JSONL and writes:

- `train.jsonl`
- `val.jsonl`
- `test.jsonl`
- `labels.json`
- `summary.json`

```bash
python3 training/text_finetune/scripts/prepare_dataset.py \
  --input training/text_finetune/data/raw.synthetic.jsonl \
  --out-dir training/text_finetune/data/processed
```

### Step 3: Train

```bash
python3 training/text_finetune/scripts/train.py \
  --data-dir training/text_finetune/data/processed \
  --output-dir training/text_finetune/runs/modernbert-text-clf \
  --base-model answerdotai/ModernBERT-base \
  --max-length 512
```

If you want sliding-window chunking for longer text, rerun with:

```bash
python3 training/text_finetune/scripts/train.py \
  --data-dir training/text_finetune/data/processed \
  --output-dir training/text_finetune/runs/modernbert-text-clf \
  --base-model answerdotai/ModernBERT-base \
  --max-length 512 \
  --stride 128
```

Training writes:

- `training/text_finetune/runs/modernbert-text-clf/model`
- `training/text_finetune/runs/modernbert-text-clf/run.json`

If you are connected over SSH, run training in a persistent session so it survives disconnects.

Using `tmux`:

```bash
tmux new -s finetune
python3 training/text_finetune/scripts/train.py \
  --data-dir training/text_finetune/data/processed \
  --output-dir training/text_finetune/runs/modernbert-text-clf \
  --base-model answerdotai/ModernBERT-base \
  --max-length 512
```

Detach with `Ctrl-b d`, then reattach later with:

```bash
tmux attach -t finetune
```

Or run it in the background with `nohup`:

```bash
nohup python3 training/text_finetune/scripts/train.py \
  --data-dir training/text_finetune/data/processed \
  --output-dir training/text_finetune/runs/modernbert-text-clf \
  --base-model answerdotai/ModernBERT-base \
  --max-length 512 \
  > training/text_finetune/runs/modernbert-text-clf/train.log 2>&1 &
```

Watch progress with:

```bash
tail -f training/text_finetune/runs/modernbert-text-clf/train.log
```

### Step 4: Evaluate

```bash
python3 training/text_finetune/scripts/evaluate.py \
  --data-dir training/text_finetune/data/processed \
  --model-dir training/text_finetune/runs/modernbert-text-clf/model
```

Evaluation writes:

- `eval/summary.json`
- `eval/confusion_matrix.csv`
- `eval/classification_report.json`

### Step 5: Export

```bash
python3 training/text_finetune/scripts/export_model.py \
  --model-dir training/text_finetune/runs/modernbert-text-clf/model \
  --export-dir training/text_finetune/runs/modernbert-text-clf/export
```

### Step 6: Test in the Docker classifier service

The main Docker stack now expects the fine-tuned exported model and loads it directly in
the classifier container.

With the default repo layout, the exported model path:

```bash
training/text_finetune/runs/modernbert-text-clf/export
```

is mounted into the classifier container as:

```bash
/models/finetuned/current
```

So after export, restart the classifier service:

```bash
docker compose up --build -d classifier api orchestrator
```

Then verify the classifier container is healthy:

```bash
docker compose ps classifier
curl http://localhost:8002/healthz
```

If your exported model lives somewhere else on the host, set:

```bash
CLASSIFIER_FINETUNED_MODEL_HOST_PATH=/absolute/path/to/exported/model
CLASSIFIER_MODEL_NAME=/models/finetuned/current
```

in `.env` before restarting Docker.

### Step 7: Upload to Hugging Face Hub

The exported folder is a standard Hugging Face model directory, so you can publish it for
other people to download and use.

Authenticate first with either:

```bash
huggingface-cli login
```

or an environment variable:

```bash
export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx
```

Then upload:

```bash
python3 training/text_finetune/scripts/push_to_hub.py \
  --folder training/text_finetune/runs/modernbert-text-clf/export \
  --repo-id your-username/doc-ocr-modernbert
```

If you want the repo private:

```bash
python3 training/text_finetune/scripts/push_to_hub.py \
  --folder training/text_finetune/runs/modernbert-text-clf/export \
  --repo-id your-username/doc-ocr-modernbert \
  --private
```

### Copy-paste command sequence

```bash
python3 -m pip install -r training/text_finetune/requirements.txt

python3 training/text_finetune/scripts/generate_synthetic_jsonl.py \
  --out training/text_finetune/data/raw.synthetic.jsonl \
  --examples-per-label 250 \
  --seed 42

python3 training/text_finetune/scripts/prepare_dataset.py \
  --input training/text_finetune/data/raw.synthetic.jsonl \
  --out-dir training/text_finetune/data/processed

python3 training/text_finetune/scripts/train.py \
  --data-dir training/text_finetune/data/processed \
  --output-dir training/text_finetune/runs/modernbert-text-clf \
  --base-model answerdotai/ModernBERT-base \
  --max-length 512

python3 training/text_finetune/scripts/evaluate.py \
  --data-dir training/text_finetune/data/processed \
  --model-dir training/text_finetune/runs/modernbert-text-clf/model

python3 training/text_finetune/scripts/export_model.py \
  --model-dir training/text_finetune/runs/modernbert-text-clf/model \
  --export-dir training/text_finetune/runs/modernbert-text-clf/export

python3 training/text_finetune/scripts/push_to_hub.py \
  --folder training/text_finetune/runs/modernbert-text-clf/export \
  --repo-id your-username/doc-ocr-modernbert
```

### Notes

- This is the canonical local path now.
- It is meant for pipeline bootstrapping and baseline experiments.
- For production accuracy, replace or supplement the synthetic data with real extracted text and verified labels.

### Step 5: Deploy (Next Step)

This scaffold stops at producing a fine-tuned Hugging Face model directory.
To use it in the platform, we still need to update `services/classifier` to load
`AutoModelForSequenceClassification` and return probabilities (instead of prototype similarity scores).

## Notes

- CPU-only training can be slow. For iteration speed, use a GPU machine if possible.
- This scaffold trains on *text only*. If you want to incorporate layout, that's a different model family (LayoutLMv3/DiT/Donut) and a different data pipeline.
