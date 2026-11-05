from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

_password_hash = PasswordHash.recommended()


def hash_password(raw: str) -> str:
    return _password_hash.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return _password_hash.verify(raw, hashed)
    except Exception:  # noqa: BLE001 - 哈希格式异常一律视为验证失败
        return False


def create_access_token(user_id: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> int:
    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )
    return int(payload["sub"])
