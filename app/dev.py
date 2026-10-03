import os
import sys
from pathlib import Path

import uvicorn

BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"


def load_env_file(path: Path) -> list[str]:
    if not path.is_file():
        return []

    loaded = []

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and value and key not in os.environ:
            os.environ[key] = value
            loaded.append(key)

    return loaded


def main() -> None:
    loaded = load_env_file(ENV_FILE)

    if loaded:
        print("Loaded from .env: " + ", ".join(loaded))

    if not os.environ.get("DATABASE_URL"):
        sys.exit(
            "DATABASE_URL is not set. Copy backend/.env.example to backend/.env "
            "and fill it in."
        )

    from app.database import get_engine
    from app.migrate import apply_migrations

    applied = apply_migrations(get_engine())

    if applied:
        print("Applied migrations: " + ", ".join(applied))

    uvicorn.run("app.main:app", host="127.0.0.1", port=int(os.environ.get("API_PORT", "8000")))


if __name__ == "__main__":
    main()
