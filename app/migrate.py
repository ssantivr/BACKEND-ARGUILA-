import os
import sys
from pathlib import Path

from sqlalchemy import Engine, text

from app.database import get_engine
from app.env import BACKEND_DIR, ENV_FILE, load_env_file, require_database_url

DEFAULT_DATABASE_DIR = BACKEND_DIR.parent / "BASE-DE-DATOS-ARQUILA"

CREATE_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""


def database_dir() -> Path:
    return Path(os.environ.get("DATABASE_DIR") or DEFAULT_DATABASE_DIR)


def migrations_dir() -> Path:
    return database_dir() / "migrations"


def seed_file() -> Path:
    return database_dir() / "seed.sql"


def apply_migrations(engine: Engine, directory: Path | None = None) -> list[str]:
    directory = directory or migrations_dir()

    if not directory.is_dir():
        raise SystemExit(
            f"Migrations folder not found: {directory}. Clone BASE-DE-DATOS-ARQUILA next to "
            "this repository or set DATABASE_DIR in .env."
        )

    with engine.begin() as connection:
        connection.exec_driver_sql(CREATE_HISTORY_TABLE)
        applied = set(connection.execute(text("SELECT version FROM schema_migrations")).scalars())

    newly_applied = []

    for path in sorted(directory.glob("*.sql")):
        if path.name in applied:
            continue

        with engine.begin() as connection:
            connection.exec_driver_sql(path.read_text(encoding="utf-8"))
            connection.execute(
                text("INSERT INTO schema_migrations (version) VALUES (:version)"),
                {"version": path.name},
            )

        newly_applied.append(path.name)

    return newly_applied


def main() -> None:
    load_env_file(ENV_FILE)
    require_database_url()

    engine = get_engine()
    applied = apply_migrations(engine)

    if applied:
        print("Applied: " + ", ".join(applied))
    else:
        print("Nothing to apply: the database is up to date")

    if "--seed" in sys.argv[1:]:
        with engine.begin() as connection:
            connection.exec_driver_sql(seed_file().read_text(encoding="utf-8"))
        print("Seed data loaded")


if __name__ == "__main__":
    main()
