#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
ENV_FILE="${ROOT_DIR}/.env"

usage() {
  cat <<'EOF'
Usage: training/text_finetune/run_docker_train.sh --data-jsonl <path> --run-name <name> [--max-length <n>] [--stride <n>]

Runs the text-only fine-tuning workflow inside Docker while reusing the Hugging Face cache
seeded by scripts/bootstrap_ec2_dev.sh.

Outputs are written under:
  <CLASSIFIER_MODEL_CACHE_HOST_PATH>/finetuned/<run-name>/
EOF
}

read_env_value() {
  local key="$1"
  local default_value="$2"
  local env_file="$3"
  local line

  if [[ ! -f "$env_file" ]]; then
    printf '%s' "$default_value"
    return
  fi

  line=$(grep -E "^${key}=" "$env_file" | tail -n 1 || true)
  if [[ -z "$line" ]]; then
    printf '%s' "$default_value"
    return
  fi

  line="${line#*=}"
  line="${line%\"}"
  line="${line#\"}"
  printf '%s' "$line"
}

DATA_JSONL=""
RUN_NAME=""
MAX_LENGTH="512"
STRIDE="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --data-jsonl)
      DATA_JSONL="$2"
      shift 2
      ;;
    --run-name)
      RUN_NAME="$2"
      shift 2
      ;;
    --max-length)
      MAX_LENGTH="$2"
      shift 2
      ;;
    --stride)
      STRIDE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$DATA_JSONL" || -z "$RUN_NAME" ]]; then
  usage >&2
  exit 1
fi

MODEL_NAME=$(read_env_value "CLASSIFIER_MODEL_NAME" "answerdotai/ModernBERT-base" "$ENV_FILE")
CACHE_HOST_PATH=$(read_env_value "CLASSIFIER_MODEL_CACHE_HOST_PATH" "/opt/doc-platform/hf-cache" "$ENV_FILE")

OUT_HOST_DIR="${CACHE_HOST_PATH}/finetuned/${RUN_NAME}"
mkdir -p "$OUT_HOST_DIR"

echo "Using model:  ${MODEL_NAME}"
echo "HF cache:     ${CACHE_HOST_PATH}"
echo "Run output:   ${OUT_HOST_DIR}"
echo "Data JSONL:   ${DATA_JSONL}"

docker build -t doc-platform-text-finetune:local -f "${ROOT_DIR}/training/text_finetune/training.Dockerfile" "${ROOT_DIR}/training/text_finetune"

docker run --rm \
  -e HF_HOME=/models/hf \
  -e CLASSIFIER_MODEL_NAME="${MODEL_NAME}" \
  -v "${CACHE_HOST_PATH}:/models/hf" \
  -v "${DATA_JSONL}:/data/raw.jsonl:ro" \
  -v "${OUT_HOST_DIR}:/out" \
  doc-platform-text-finetune:local \
  bash -lc "\
    python3 /workspace/scripts/prepare_dataset.py --input /data/raw.jsonl --out-dir /out/data/processed && \
    python3 /workspace/scripts/train.py --data-dir /out/data/processed --output-dir /out --base-model \"${MODEL_NAME}\" --max-length \"${MAX_LENGTH}\" --stride \"${STRIDE}\" && \
    python3 /workspace/scripts/evaluate.py --data-dir /out/data/processed --model-dir /out/model --max-length \"${MAX_LENGTH}\" --out-dir /out/eval && \
    python3 /workspace/scripts/export_model.py --model-dir /out/model --export-dir /out/export \
  "

cat <<EOF

Done.

Artifacts:
  ${OUT_HOST_DIR}/model        (fine-tuned HF directory)
  ${OUT_HOST_DIR}/export       (deployment-friendly copy)
  ${OUT_HOST_DIR}/eval         (metrics + confusion matrix)

Next (integration):
  - Mount ${CACHE_HOST_PATH} into the classifier container (already done in docker-compose.yml)
  - Update the classifier runtime to load AutoModelForSequenceClassification from:
      /models/huggingface/finetuned/${RUN_NAME}/model
EOF

