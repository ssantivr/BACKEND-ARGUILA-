import hashlib

import pytest
from sqlalchemy import select

from app.database import get_session
from app.main import app
from app.models import User
from app.security import hash_password, needs_rehash, verify_password
from tests.helpers import PASSWORD, register


def legacy_hash(password, salt=b"0123456789abcdef"):
    key = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${key.hex()}"


def test_password_hash_uses_argon2_and_verifies_only_the_same_password():
    stored = hash_password("correct-horse-battery")

    assert stored.startswith("$argon2id$")
    assert "correct-horse-battery" not in stored
    assert verify_password("correct-horse-battery", stored)
    assert not verify_password("wrong-password", stored)
    assert not needs_rehash(stored)


def test_same_password_gets_a_different_hash_each_time():
    assert hash_password("correct-horse-battery") != hash_password("correct-horse-battery")


@pytest.mark.parametrize(
    "stored",
    [
        None,
        "",
        "plain-text",
        "scrypt$only-two-parts",
        "scrypt$zz$zz",
        "a$b$c$d",
        "$argon2id$broken",
        "$argon2id$v=19$m=65536,t=3,p=4$c2FsdA$",
    ],
)
def test_malformed_stored_hash_never_verifies(stored):
    assert not verify_password("correct-horse-battery", stored)
    assert needs_rehash(stored)


def test_legacy_scrypt_hash_still_verifies_and_asks_for_a_rehash():
    stored = legacy_hash("correct-horse-battery")

    assert verify_password("correct-horse-battery", stored)
    assert not verify_password("wrong-password", stored)
    assert needs_rehash(stored)


def test_hash_with_another_scheme_never_verifies():
    _, salt, key = legacy_hash("correct-horse-battery").split("$")

    assert not verify_password("correct-horse-battery", f"md5${salt}${key}")


def stored_hash(email):
    session = next(app.dependency_overrides[get_session]())

    return session.scalar(select(User.password_hash).where(User.email == email))


def test_login_upgrades_a_legacy_hash_to_argon2(client):
    user = register(client)
    session = next(app.dependency_overrides[get_session]())
    account = session.get(User, user["id"])
    account.password_hash = legacy_hash(PASSWORD)
    session.commit()

    wrong = client.post("/auth/login", json={"email": user["email"], "password": "wrong-password"})

    assert wrong.status_code == 401
    assert stored_hash(user["email"]).startswith("scrypt$")

    right = client.post("/auth/login", json={"email": user["email"], "password": PASSWORD})

    assert right.status_code == 200
    assert stored_hash(user["email"]).startswith("$argon2id$")

    again = client.post("/auth/login", json={"email": user["email"], "password": PASSWORD})

    assert again.status_code == 200
