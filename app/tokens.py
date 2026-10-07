import hashlib
import os
from datetime import UTC, datetime, timedelta

import jwt

ALGORITHM = "HS256"
ISSUER = "arquila"
ACCESS_TOKEN_LIFETIME = timedelta(minutes=15)
MIN_SECRET_BYTES = 32
FINGERPRINT_LENGTH = 16


def signing_secret() -> str | None:
    secret = os.environ.get("JWT_SECRET", "")

    return secret if len(secret.encode("utf-8")) >= MIN_SECRET_BYTES else None


def password_fingerprint(password_hash: str | None) -> str:
    digest = hashlib.sha256((password_hash or "").encode("utf-8")).hexdigest()

    return digest[:FINGERPRINT_LENGTH]


def create_access_token(user_id: int, password_hash: str | None) -> str | None:
    secret = signing_secret()

    if secret is None:
        return None

    now = datetime.now(UTC)
    claims = {
        "iss": ISSUER,
        "sub": str(user_id),
        "iat": now,
        "exp": now + ACCESS_TOKEN_LIFETIME,
        "pwd": password_fingerprint(password_hash),
    }

    return jwt.encode(claims, secret, algorithm=ALGORITHM)


def read_access_token(token: str) -> tuple[int, str] | None:
    secret = signing_secret()

    if secret is None:
        return None

    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            options={"require": ["exp", "iat", "iss", "sub", "pwd"]},
        )

        return int(claims["sub"]), str(claims["pwd"])
    except (jwt.InvalidTokenError, ValueError):
        return None
