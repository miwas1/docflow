from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "training" / "text_finetune" / "scripts" / "train.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("train_script", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_training_args_uses_eval_strategy_when_supported() -> None:
    module = _load_module()

    class NewTrainingArguments:
        def __init__(self, output_dir, eval_strategy=None, save_strategy=None, **kwargs):
            self.output_dir = output_dir
            self.eval_strategy = eval_strategy
            self.save_strategy = save_strategy
            self.kwargs = kwargs

    args = module._build_training_arguments(
        NewTrainingArguments,
        output_dir="out",
        num_train_epochs=3,
        learning_rate=2e-5,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=16,
        seed=1337,
    )

    assert args.eval_strategy == "epoch"
    assert args.save_strategy == "epoch"


def test_training_args_uses_evaluation_strategy_when_supported() -> None:
    module = _load_module()

    class OldTrainingArguments:
        def __init__(self, output_dir, evaluation_strategy=None, save_strategy=None, **kwargs):
            self.output_dir = output_dir
            self.evaluation_strategy = evaluation_strategy
            self.save_strategy = save_strategy
            self.kwargs = kwargs

    args = module._build_training_arguments(
        OldTrainingArguments,
        output_dir="out",
        num_train_epochs=3,
        learning_rate=2e-5,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=16,
        seed=1337,
    )

    assert args.evaluation_strategy == "epoch"
    assert args.save_strategy == "epoch"
