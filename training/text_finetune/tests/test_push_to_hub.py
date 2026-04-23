from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "training" / "text_finetune" / "scripts" / "push_to_hub.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("push_to_hub", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upload_folder_creates_repo_and_uploads_folder(tmp_path: Path) -> None:
    module = _load_module()
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    (model_dir / "config.json").write_text('{"model_type":"bert"}\n', encoding="utf-8")

    calls: list[tuple[str, dict]] = []

    class FakeApi:
        def create_repo(self, **kwargs):
            calls.append(("create_repo", kwargs))
            return {"repo_id": kwargs["repo_id"]}

        def upload_folder(self, **kwargs):
            calls.append(("upload_folder", kwargs))
            return {"commit_url": "https://huggingface.co/test-user/test-model/commit/123"}

    result = module.upload_folder_to_hub(
        folder_path=model_dir,
        repo_id="test-user/test-model",
        private=True,
        commit_message="Upload model",
        token="hf_test_token",
        api=FakeApi(),
    )

    assert result["repo_id"] == "test-user/test-model"
    assert calls == [
        (
            "create_repo",
            {
                "repo_id": "test-user/test-model",
                "repo_type": "model",
                "private": True,
                "exist_ok": True,
                "token": "hf_test_token",
            },
        ),
        (
            "upload_folder",
            {
                "folder_path": str(model_dir),
                "repo_id": "test-user/test-model",
                "repo_type": "model",
                "commit_message": "Upload model",
                "token": "hf_test_token",
            },
        ),
    ]

