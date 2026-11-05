"""字段级加密（AES-256-GCM）。

保护的是"数据库或备份泄露"这一层：
即使 dump 被拿走，秘密和日记也读不出来。

注意：这是服务端加密，不是端到端加密。拥有服务器和密钥的人仍然可以解密。
"""

import base64
import hashlib
import os
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

_PREFIX = "v1:"
_NONCE_SIZE = 12


@lru_cache(maxsize=4)
def _derive_key(raw: str) -> bytes:
    return hashlib.sha256(raw.encode()).digest()


def _key() -> bytes:
    raw = settings.DATA_ENCRYPTION_KEY
    if not raw:
        if settings.ENV == "prod":
            raise RuntimeError("生产环境必须配置 DATA_ENCRYPTION_KEY")
        # 开发环境用 JWT_SECRET 派生，保证本地能直接跑
        raw = settings.JWT_SECRET
    return _derive_key(raw)


def ensure_configured() -> None:
    """生产环境启动时检查密钥，避免上线后才发现。"""
    if settings.ENV == "prod" and not settings.DATA_ENCRYPTION_KEY:
        raise RuntimeError("生产环境必须配置 DATA_ENCRYPTION_KEY")


def encrypt(plaintext: str | None) -> str | None:
    if plaintext is None:
        return None
    if plaintext.startswith(_PREFIX):
        # 已经是密文，避免重复加密
        return plaintext

    nonce = os.urandom(_NONCE_SIZE)
    ciphertext = AESGCM(_key()).encrypt(nonce, plaintext.encode(), None)
    return _PREFIX + base64.b64encode(nonce + ciphertext).decode()


def decrypt(token: str | None) -> str | None:
    if token is None:
        return None
    if not token.startswith(_PREFIX):
        # 兼容历史明文数据
        return token

    raw = base64.b64decode(token[len(_PREFIX) :])
    nonce, ciphertext = raw[:_NONCE_SIZE], raw[_NONCE_SIZE:]
    return AESGCM(_key()).decrypt(nonce, ciphertext, None).decode()
