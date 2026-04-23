#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path


def _resolve_token(cli_token: str | None) -> str | None:
    if cli_token:
        return cli_token
    return os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")


def upload_folder_to_hub(
    *,
    folder_path: Path,
    repo_id: str,
    private: bool,
    commit_message: str,
    token: str | None,
    api=None,
) -> dict[str, str]:
    if not folder_path.exists():
        raise SystemExit(f"Missing folder to upload: {folder_path}")

    if api is None:
        from huggingface_hub import HfApi

        api = HfApi()

    api.create_repo(
        repo_id=repo_id,
        repo_type="model",
        private=private,
        exist_ok=True,
        token=token,
    )
    api.upload_folder(
        folder_path=str(folder_path),
        repo_id=repo_id,
        repo_type="model",
        commit_message=commit_message,
        token=token,
    )
    return {"repo_id": repo_id, "folder_path": str(folder_path)}


def main() -> None:
    ap = argparse.ArgumentParser(description="Upload a fine-tuned model folder to the Hugging Face Hub.")
    ap.add_argument(
        "--folder",
        required=True,
        help="Local model directory to upload, for example training/text_finetune/runs/modernbert-text-clf/export",
    )
    ap.add_argument("--repo-id", required=True, help="Target Hub repo id, for example your-username/doc-ocr-modernbert")
    ap.add_argument("--token", default=None, help="Optional Hugging Face token. Defaults to HF_TOKEN/HUGGING_FACE_HUB_TOKEN or saved login.")
    ap.add_argument("--private", action="store_true", help="Create the repo as private.")
    ap.add_argument("--commit-message", default="Upload fine-tuned model", help="Commit message to use for the upload.")
    args = ap.parse_args()

    folder_path = Path(args.folder)
    token = _resolve_token(args.token)

    result = upload_folder_to_hub(
        folder_path=folder_path,
        repo_id=args.repo_id,
        private=args.private,
        commit_message=args.commit_message,
        token=token,
    )

    print(f"Uploaded {result['folder_path']} to https://huggingface.co/{result['repo_id']}")


if __name__ == "__main__":
    main()
