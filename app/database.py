import os
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine() -> Engine:
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")

    return create_engine(database_url, pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
