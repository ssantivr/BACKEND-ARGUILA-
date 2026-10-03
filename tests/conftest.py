import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, make_url
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base, get_session
from app.main import app
from app.migrate import apply_migrations
from app.services.login_limiter import login_limiter
from app.services.undo_history import undo_history


def create_test_engine() -> Engine:
    url = os.environ.get("TEST_DATABASE_URL")

    if url is None:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        return engine

    if not (make_url(url).database or "").endswith("test"):
        raise RuntimeError(
            "TEST_DATABASE_URL must point to a database whose name ends in 'test': "
            "every table in it is emptied before each test"
        )

    engine = create_engine(url)
    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)

    apply_migrations(engine)

    with engine.begin() as connection:
        connection.exec_driver_sql(f"TRUNCATE {tables} RESTART IDENTITY CASCADE")

    return engine


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))

    engine = create_test_engine()

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    yield TestClient(app)

    app.dependency_overrides.clear()
    undo_history.clear()
    login_limiter.clear()
    engine.dispose()
