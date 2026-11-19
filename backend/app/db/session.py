from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    url = get_settings().database_url
    args = {"prepare_threshold": None} if ":6543/" in url else {}      # Supabase transaction pooler (6543) cannot keep prepared statements
    return create_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=10, connect_args=args)


@lru_cache
def _factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def SessionLocal() -> Session:  # noqa: N802
    return _factory()()


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
