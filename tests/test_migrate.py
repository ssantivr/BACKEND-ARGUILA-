import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app import migrate
from app.migrate import apply_migrations, migrations_dir


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
    names = sorted(path.name for path in migrations_dir().glob("*.sql"))
    numbers = [int(name.split("_")[0]) for name in names]

    assert names, "there must be at least the initial migration"
    assert numbers == list(range(1, len(names) + 1))


def test_command_reads_the_database_url_from_the_env_file(tmp_path, monkeypatch, capsys):
    database = tmp_path / "command.db"
    env_file = tmp_path / ".env"
    env_file.write_text(f"DATABASE_URL=sqlite:///{database.as_posix()}\n", encoding="utf-8")
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "001_first.sql").write_text("CREATE TABLE first (id INTEGER)", encoding="utf-8")
    seed = tmp_path / "seed.sql"
    seed.write_text("INSERT INTO first (id) VALUES (7)", encoding="utf-8")

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(migrate, "ENV_FILE", env_file)
    monkeypatch.setenv("DATABASE_DIR", str(tmp_path))
    monkeypatch.setattr(migrate.sys, "argv", ["migrate", "--seed"])
    migrate.get_engine.cache_clear()

    try:
        migrate.main()

        with migrate.get_engine().connect() as connection:
            assert connection.execute(text("SELECT id FROM first")).scalars().all() == [7]
    finally:
        migrate.get_engine().dispose()
        migrate.get_engine.cache_clear()

    output = capsys.readouterr().out

    assert "Applied: 001_first.sql" in output
    assert "Seed data loaded" in output


def test_command_stops_with_a_clear_message_without_a_database_url(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(migrate, "ENV_FILE", tmp_path / "missing.env")

    with pytest.raises(SystemExit, match=".env"):
        migrate.main()
