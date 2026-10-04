import sys
from pathlib import Path

from sqlalchemy import Engine, text

from app.database import get_engine
from app.env import ENV_FILE, load_env_file, require_database_url

DATABASE_DIR = Path(__file__).resolve().parents[2] / "database"
MIGRATIONS_DIR = DATABASE_DIR / "migrations"
SEED_FILE = DATABASE_DIR / "seed.sql"

CREATE_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""


def apply_migrations(engine: Engine, directory: Path = MIGRATIONS_DIR) -> list[str]:
    with engine.begin() as connection:
        connection.exec_driver_sql(CREATE_HISTORY_TABLE)
        applied = set(
            connection.execute(text("SELECT version FROM schema_migrations")).scalars()
        )

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
    applied = apply_migrations(engine, MIGRATIONS_DIR)

    if applied:
        print("Applied: " + ", ".join(applied))
    else:
        print("Nothing to apply: the database is up to date")

    if "--seed" in sys.argv[1:]:
        with engine.begin() as connection:
            connection.exec_driver_sql(SEED_FILE.read_text(encoding="utf-8"))
        print("Seed data loaded")


if __name__ == "__main__":
    main()
