#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from typing import Iterable
from urllib import error, request as urllib_request
from uuid import uuid4


SUPPORTED_MEDIA_TYPES_BY_EXT = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def _read_env_value(env_path: Path, key: str, default: str) -> str:
    if not env_path.exists():
        return default
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() != key:
            continue
        v = v.strip().strip('"')
        return v
    return default


def _iter_input_files(input_dir: Path) -> Iterable[Path]:
    for path in sorted(input_dir.rglob("*")):
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext in SUPPORTED_MEDIA_TYPES_BY_EXT:
            yield path


def _derive_label(path: Path, *, input_dir: Path, label_mode: str, constant_label: str | None) -> str:
    if label_mode == "folder":
        # Expect: <input_dir>/<label>/<file>
        rel = path.relative_to(input_dir)
        if len(rel.parts) < 2:
            raise ValueError(f"Cannot infer label from folder for {rel} (expected <label>/<file>)")
        return rel.parts[0]
    if label_mode == "constant":
        if not constant_label:
            raise ValueError("Missing --label for label-mode=constant")
        return constant_label
    raise ValueError(f"Unsupported label-mode: {label_mode}")


def _extract_via_service(
    *,
    extractor_url: str,
    tenant_id: str,
    source_media_type: str,
    source_filename: str,
    content: bytes,
    timeout_seconds: float,
) -> dict:
    payload = {
        "job_id": f"train-{uuid4()}",
        "document_id": f"train-{uuid4()}",
        "tenant_id": tenant_id,
        "source_media_type": source_media_type,
        "source_filename": source_filename,
        "source_artifact_id": f"train-artifact-{uuid4()}",
        "inline_content_base64": base64.b64encode(content).decode("utf-8"),
    }

    req = urllib_request.Request(
        url=f"{extractor_url.rstrip('/')}/v1/extractions:run",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=timeout_seconds) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Generate labeled training JSONL by extracting text from documents via the running extractor service.\n\n"
            "Recommended dataset layout for label-mode=folder:\n"
            "  <input-dir>/invoice/*.pdf\n"
            "  <input-dir>/receipt/*.png\n"
            "  <input-dir>/bank_statement/*.pdf\n"
        )
    )
    ap.add_argument("--input-dir", required=True, help="Directory containing labeled subfolders of documents.")
    ap.add_argument("--out", required=True, help="Output JSONL path to write (raw.jsonl).")
    ap.add_argument("--label-mode", choices=["folder", "constant"], default="folder")
    ap.add_argument("--label", default=None, help="Label to apply when --label-mode=constant.")
    ap.add_argument("--tenant-id", default="training", help="Tenant id to include in extraction payloads.")
    ap.add_argument("--extractor-url", default=None, help="Extractor base URL (default from .env EXTRACTOR_BASE_URL or http://localhost:8001).")
    ap.add_argument("--timeout-seconds", type=float, default=60.0)
    ap.add_argument("--limit", type=int, default=0, help="If >0, process at most N files.")
    ap.add_argument("--skip-errors", action="store_true", help="Continue on extraction errors (writes error metadata).")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    env_path = repo_root / ".env"

    extractor_url = args.extractor_url or _read_env_value(env_path, "EXTRACTOR_BASE_URL", "http://localhost:8001")
    input_dir = Path(args.input_dir)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    files = list(_iter_input_files(input_dir))
    if args.limit and args.limit > 0:
        files = files[: args.limit]
    if not files:
        raise SystemExit("No supported files found under input-dir.")

    processed = 0
    errors = 0

    with out_path.open("w", encoding="utf-8") as f:
        for path in files:
            rel = path.relative_to(input_dir).as_posix()
            ext = path.suffix.lower()
            media_type = SUPPORTED_MEDIA_TYPES_BY_EXT[ext]

            try:
                label = _derive_label(
                    path, input_dir=input_dir, label_mode=args.label_mode, constant_label=args.label
                )
            except Exception as exc:
                raise SystemExit(str(exc)) from exc

            sys.stderr.write(f"[extract] {rel} ({media_type}) -> label={label}\n")
            sys.stderr.flush()

            row = {
                "id": rel,
                "label": label,
                "source_media_type": media_type,
            }

            try:
                content = path.read_bytes()
                resp = _extract_via_service(
                    extractor_url=extractor_url,
                    tenant_id=args.tenant_id,
                    source_media_type=media_type,
                    source_filename=path.name,
                    content=content,
                    timeout_seconds=args.timeout_seconds,
                )
                row["text"] = resp.get("text", "") or ""
                row["extraction_path"] = resp.get("extraction_path")
                row["fallback_used"] = resp.get("fallback_used")
                row["fallback_reason"] = resp.get("fallback_reason")
                row["page_count"] = resp.get("page_count")
            except (error.HTTPError, error.URLError, TimeoutError, Exception) as exc:
                errors += 1
                if not args.skip_errors:
                    raise
                row["text"] = ""
                row["error"] = str(exc)

            f.write(json.dumps(row, ensure_ascii=True) + "\n")
            processed += 1

    summary = {"processed": processed, "errors": errors, "out": str(out_path), "extractor_url": extractor_url}
    sys.stderr.write(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()

