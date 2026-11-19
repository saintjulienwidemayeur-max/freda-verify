from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Every table lives in its own PostgreSQL schema so Freda Verify can share a database (e.g. a Supabase project that already
# hosts other applications in `public`) without ever touching their tables. Fixed name: same in dev, tests and production.
SCHEMA = "freda_verify"


def fk(target: str) -> str:
    """'organizations.id' -> 'freda_verify.organizations.id' (ForeignKey targets must be schema-qualified)."""
    return f"{SCHEMA}.{target}"


class Base(DeclarativeBase):
    metadata = MetaData(schema=SCHEMA)
