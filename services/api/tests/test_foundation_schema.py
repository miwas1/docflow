from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from api_service.db.base import Base
from api_service.db import models  # noqa: F401


def load_migration_module():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0001_foundation_schema.py"
    )
    spec = spec_from_file_location("foundation_schema", migration_path)
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_orm_models_expose_expected_phase_one_tables() -> None:
    assert {"jobs", "job_events", "artifacts", "model_versions"}.issubset(set(Base.metadata.tables))


def test_migration_module_tracks_expected_phase_one_tables() -> None:
    migration = load_migration_module()

    assert tuple(migration.TABLE_NAMES) == ("jobs", "job_events", "artifacts", "model_versions")
