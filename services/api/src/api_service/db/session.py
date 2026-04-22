"""Database session helpers."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from api_service.config import get_settings


def build_engine(database_url: str | None = None) -> Engine:
    settings = get_settings()
    return create_engine(database_url or settings.postgres_dsn, future=True)


def build_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    return sessionmaker(bind=build_engine(database_url), autoflush=False, autocommit=False, future=True)
