import os

from app.dev import load_env_file


def test_missing_file_loads_nothing(tmp_path):
    assert load_env_file(tmp_path / ".env") == []


def test_loads_values_and_skips_comments_blanks_and_empty_values(tmp_path, monkeypatch):
    for key in ("ARQ_TEST_URL", "ARQ_TEST_QUOTED", "ARQ_TEST_EMPTY", "ARQ_TEST_KEPT"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("ARQ_TEST_KEPT", "from the real environment")

    path = tmp_path / ".env"
    path.write_text(
        "# a comment\n"
        "\n"
        "ARQ_TEST_URL=postgresql+psycopg://user:pa=ss@localhost:5432/db\n"
        'ARQ_TEST_QUOTED = "hello world"\n'
        "ARQ_TEST_EMPTY=\n"
        "ARQ_TEST_KEPT=from the file\n"
        "not a setting\n",
        encoding="utf-8",
    )

    try:
        assert load_env_file(path) == ["ARQ_TEST_URL", "ARQ_TEST_QUOTED"]
        assert os.environ["ARQ_TEST_URL"] == "postgresql+psycopg://user:pa=ss@localhost:5432/db"
        assert os.environ["ARQ_TEST_QUOTED"] == "hello world"
        assert "ARQ_TEST_EMPTY" not in os.environ
        assert os.environ["ARQ_TEST_KEPT"] == "from the real environment"
    finally:
        os.environ.pop("ARQ_TEST_URL", None)
        os.environ.pop("ARQ_TEST_QUOTED", None)
