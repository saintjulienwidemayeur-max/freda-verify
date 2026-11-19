from logging.config import fileConfig

from sqlalchemy import create_engine, text

from alembic import context
from app import models  # noqa: F401  (registers the tables on Base.metadata)
from app.core.config import get_settings
from app.db.base import SCHEMA, Base

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata
LOCK_ID = 727_274_001   # advisory lock: two containers starting together must not migrate at the same time


def include_object(obj, name, type_, reflected, compare_to):
    """Only ever look at OUR schema (the database may host other applications in `public`)."""
    if type_ == "table":
        return getattr(obj, "schema", None) == SCHEMA
    return True


OPTS = dict(target_metadata=target_metadata, compare_type=True, include_schemas=True, version_table_schema=SCHEMA, include_object=include_object)


def run_migrations_offline() -> None:
    context.configure(url=get_settings().database_url, literal_binds=True, **OPTS)
    with context.begin_transaction():
        context.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(get_settings().database_url)
    with engine.connect() as connection:
        connection.execute(text("SELECT pg_advisory_lock(:id)"), {"id": LOCK_ID})
        try:
            connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
            connection.commit()
            context.configure(connection=connection, **OPTS)
            with context.begin_transaction():
                context.run_migrations()
        finally:
            connection.rollback()
            connection.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": LOCK_ID})
            connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
