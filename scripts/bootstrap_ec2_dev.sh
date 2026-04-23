#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
TARGET_USER="${SUDO_USER:-${USER}}"
SKIP_DOCKER_INSTALL=0
CACHE_DIR_OVERRIDE=""
SKIP_MODEL_DOWNLOAD=0
BASE_MODEL_OVERRIDE=""

usage() {
  cat <<'EOF'
Usage: scripts/bootstrap_ec2_dev.sh [--user <linux-user>] [--cache-dir <path>] [--skip-docker-install] [--skip-model-download] [--base-model <hf-repo-id>]

One-time bootstrap for CPU-based fine-tuning + classifier development on EC2 or another Linux Docker host.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --user)
      TARGET_USER="$2"
      shift 2
      ;;
    --cache-dir)
      CACHE_DIR_OVERRIDE="$2"
      shift 2
      ;;
    --skip-docker-install)
      SKIP_DOCKER_INSTALL=1
      shift
      ;;
    --skip-model-download)
      SKIP_MODEL_DOWNLOAD=1
      shift
      ;;
    --base-model)
      BASE_MODEL_OVERRIDE="$2"
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

read_env_value() {
  local key="$1"
  local default_value="$2"
  local env_file="$3"
  local line

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

ensure_env_file() {
  if [[ ! -f "${ROOT_DIR}/.env" ]]; then
    cp "${ROOT_DIR}/.env.example" "${ROOT_DIR}/.env"
    echo "Created ${ROOT_DIR}/.env from .env.example"
  fi
}

install_docker() {
  if command -v docker >/dev/null 2>&1; then
    return
  fi

  if [[ "$SKIP_DOCKER_INSTALL" -eq 1 ]]; then
    echo "Docker is missing and --skip-docker-install was set." >&2
    exit 1
  fi

  if command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y docker docker-compose-plugin || sudo dnf install -y docker
  elif command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y docker.io docker-compose-plugin || sudo apt-get install -y docker.io
  else
    echo "Unsupported host. Install Docker manually, then re-run this script." >&2
    exit 1
  fi
}

ensure_docker_running() {
  sudo systemctl enable --now docker
  if ! getent group docker >/dev/null 2>&1; then
    sudo groupadd docker
  fi
  if ! id -nG "$TARGET_USER" | tr ' ' '\n' | grep -qx docker; then
    sudo usermod -aG docker "$TARGET_USER"
    echo "Added ${TARGET_USER} to the docker group. You may need to log out and back in after setup."
  fi
}

docker_cmd() {
  if docker info >/dev/null 2>&1; then
    docker "$@"
  else
    sudo docker "$@"
  fi
}

ensure_cache_dir() {
  local cache_dir="$1"
  sudo mkdir -p "$cache_dir"
  sudo chown -R "$TARGET_USER":"$TARGET_USER" "$cache_dir"
}

download_model_snapshot() {
  local model_name="$1"
  local cache_dir="$2"

  echo "Downloading ${model_name} into ${cache_dir}"

  docker_cmd run --rm \
    -e HF_HOME=/hf-cache \
    -e MODEL_NAME="$model_name" \
    -v "${cache_dir}:/hf-cache" \
    python:3.12-slim \
    bash -lc "pip install --quiet 'huggingface_hub>=0.31,<1.0' && python -c \"import os; from huggingface_hub import snapshot_download; snapshot_download(repo_id=os.environ['MODEL_NAME'], cache_dir=os.environ['HF_HOME'])\""
}

ensure_env_file

ENV_FILE="${ROOT_DIR}/.env"
# The classifier now points CLASSIFIER_MODEL_NAME at a *local fine-tuned model directory* (e.g. /models/finetuned/current).
# For bootstrap we seed the base model into the HF cache so CPU fine-tuning can run with local_files_only=true.
BASE_MODEL_NAME=$(read_env_value "TEXT_FINETUNE_BASE_MODEL_NAME" "answerdotai/ModernBERT-base" "$ENV_FILE")
if [[ -n "$BASE_MODEL_OVERRIDE" ]]; then
  BASE_MODEL_NAME="$BASE_MODEL_OVERRIDE"
fi
DEFAULT_CACHE_DIR=$(read_env_value "CLASSIFIER_MODEL_CACHE_HOST_PATH" "/opt/doc-platform/hf-cache" "$ENV_FILE")
CACHE_DIR="${CACHE_DIR_OVERRIDE:-$DEFAULT_CACHE_DIR}"

install_docker
ensure_docker_running
ensure_cache_dir "$CACHE_DIR"
if [[ "$SKIP_MODEL_DOWNLOAD" -eq 0 ]]; then
  download_model_snapshot "$BASE_MODEL_NAME" "$CACHE_DIR"
fi

cat <<EOF

Bootstrap complete.

Model cache: ${CACHE_DIR}
Base model:  ${BASE_MODEL_NAME}

Next steps:
  cd ${ROOT_DIR}
  docker compose up --build

If docker permissions do not apply in your current shell yet, re-login or run:
  newgrp docker
EOF
