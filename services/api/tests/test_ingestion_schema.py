from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from api_service.db.base import Base
from api_service.db import models  # noqa: F401


def load_migration_module():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0002_ingestion_contract.py"
    )
    spec = spec_from_file_location("ingestion_contract", migration_path)
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_orm_models_expose_ingestion_tables_and_columns() -> None:
    assert "api_clients" in Base.metadata.tables

    jobs_columns = Base.metadata.tables["jobs"].columns.keys()
    assert "client_id" in jobs_columns
    assert "idempotency_key" in jobs_columns
    assert "failure_code" in jobs_columns
    assert "failure_message" in jobs_columns


def test_migration_module_tracks_ingestion_tables_and_columns() -> None:
    migration = load_migration_module()

    assert "api_clients" in migration.TABLE_NAMES
    assert "client_id" in migration.JOB_COLUMNS
    assert "idempotency_key" in migration.JOB_COLUMNS
    assert "failure_code" in migration.JOB_COLUMNS
    assert "failure_message" in migration.JOB_COLUMNS
