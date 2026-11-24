from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from ..config import get_settings

_ph = PasswordHasher()
TOKEN_DAYS = 90


def hash_password(pw: str) -> str:
    return _ph.hash(pw)


def verify_password(pw_hash: str, pw: str) -> bool:
    try:
        return _ph.verify(pw_hash, pw)
    except VerifyMismatchError:
        return False


def make_token(user_id: UUID, foyer_id: UUID) -> str:
    exp = datetime.now(UTC) + timedelta(days=TOKEN_DAYS)
    return jwt.encode({"sub": str(user_id), "foyer": str(foyer_id), "exp": exp},
                      get_settings().jwt_secret, algorithm="HS256")


def foyer_from_token(token: str) -> UUID | None:
    try:
        return UUID(jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])["foyer"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
