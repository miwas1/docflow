import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api_service.auth import authenticate_api_key
from api_service.config import APISettings
from api_service.db.base import Base
from api_service.errors import APIError
from api_service.main import app


@pytest.fixture()
def api_settings() -> APISettings:
    return APISettings(
        postgres_dsn="sqlite+pysqlite:///:memory:",
        rabbitmq_url="amqp://guest:guest@localhost:5672//",
        object_storage_endpoint="http://localhost:9000",
        object_storage_bucket="doc-platform-artifacts",
        object_storage_access_key="minioadmin",
        object_storage_secret_key="minioadmin",
        api_key_header_name="X-API-Key",
        api_keys_json={"demo-client": "demo-secret-key"},
        max_upload_bytes=1024 * 1024,
        host="127.0.0.1",
        port=8000,
        log_level="INFO",
    )


@pytest.fixture()
def session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    with factory() as db_session:
        yield db_session


def test_missing_api_key_returns_401(api_settings: APISettings, session: Session) -> None:
    with pytest.raises(APIError) as exc_info:
        authenticate_api_key(api_key=None, settings=api_settings, session=session)

    assert exc_info.value.status_code == 401
    assert exc_info.value.error_code == "unauthorized"


def test_upload_route_is_registered() -> None:
    route = next(route for route in app.routes if route.path == "/v1/documents:upload")

    assert route.methods == {"POST"}
