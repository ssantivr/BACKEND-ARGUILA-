import pytest

from app.database import database_url


@pytest.mark.parametrize("scheme", ["postgres", "postgresql"])
def test_plain_postgres_urls_use_the_installed_driver(scheme):
    url = database_url(f"{scheme}://user:secret@host:5432/arquila?sslmode=require")

    assert url.drivername == "postgresql+psycopg"
    assert url.password == "secret"
    assert url.query == {"sslmode": "require"}


@pytest.mark.parametrize("value", ["postgresql+psycopg://user@host/arquila", "sqlite://"])
def test_other_urls_are_left_as_they_are(value):
    assert database_url(value).render_as_string(hide_password=False) == value
