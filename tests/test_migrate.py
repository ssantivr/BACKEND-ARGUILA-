import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.migrate import MIGRATIONS_DIR, apply_migrations


@pytest.fixture
def engine():
    engine = create_engine("sqlite://")
    yield engine
    engine.dispose()


def write(directory, name, sql):
    (directory / name).write_text(sql, encoding="utf-8")


def versions(engine):
    with engine.connect() as connection:
        rows = connection.execute(text("SELECT version FROM schema_migrations ORDER BY version"))
        return list(rows.scalars())


def test_applies_pending_migrations_in_order_and_only_once(engine, tmp_path):
    write(tmp_path, "002_add_color.sql", "ALTER TABLE things ADD COLUMN color VARCHAR(20)")
    write(tmp_path, "001_create_things.sql", "CREATE TABLE things (id INTEGER PRIMARY KEY)")

    assert apply_migrations(engine, tmp_path) == ["001_create_things.sql", "002_add_color.sql"]
    assert versions(engine) == ["001_create_things.sql", "002_add_color.sql"]
    assert [c["name"] for c in inspect(engine).get_columns("things")] == ["id", "color"]

    assert apply_migrations(engine, tmp_path) == []

    write(tmp_path, "003_add_size.sql", "ALTER TABLE things ADD COLUMN size INTEGER")

    assert apply_migrations(engine, tmp_path) == ["003_add_size.sql"]
    assert len(versions(engine)) == 3


def test_failed_migration_is_not_recorded_and_stops_the_run(engine, tmp_path):
    write(tmp_path, "001_create_things.sql", "CREATE TABLE things (id INTEGER PRIMARY KEY)")
    write(tmp_path, "002_broken.sql", "ALTER TABLE missing_table ADD COLUMN x INTEGER")
    write(tmp_path, "003_never_reached.sql", "CREATE TABLE later (id INTEGER PRIMARY KEY)")

    with pytest.raises(SQLAlchemyError):
        apply_migrations(engine, tmp_path)

    assert versions(engine) == ["001_create_things.sql"]
    assert "later" not in inspect(engine).get_table_names()


def test_project_migrations_are_numbered_without_gaps():
    names = sorted(path.name for path in MIGRATIONS_DIR.glob("*.sql"))
    numbers = [int(name.split("_")[0]) for name in names]

    assert names, "there must be at least the initial migration"
    assert numbers == list(range(1, len(names) + 1))
