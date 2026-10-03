import hashlib
import hmac
import secrets

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
KEY_BYTES = 32


def _derive(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=KEY_BYTES,
    )


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    return f"scrypt${salt.hex()}${_derive(password, salt).hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    try:
        scheme, salt_hex, key_hex = (stored or "").split("$")
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(key_hex)
    except ValueError:
        return False

    if scheme != "scrypt":
        return False

    return hmac.compare_digest(_derive(password, salt), expected)


DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(16))


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
