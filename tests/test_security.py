import pytest

from app.security import hash_password, verify_password


def test_password_hash_verifies_only_the_same_password():
    stored = hash_password("correct-horse-battery")

    assert stored.startswith("scrypt$")
    assert "correct-horse-battery" not in stored
    assert verify_password("correct-horse-battery", stored)
    assert not verify_password("wrong-password", stored)


def test_same_password_gets_a_different_hash_each_time():
    assert hash_password("correct-horse-battery") != hash_password("correct-horse-battery")


@pytest.mark.parametrize(
    "stored",
    [None, "", "plain-text", "scrypt$only-two-parts", "scrypt$zz$zz", "a$b$c$d"],
)
def test_malformed_stored_hash_never_verifies(stored):
    assert not verify_password("correct-horse-battery", stored)


def test_hash_with_another_scheme_never_verifies():
    _, salt, key = hash_password("correct-horse-battery").split("$")

    assert not verify_password("correct-horse-battery", f"md5${salt}${key}")
