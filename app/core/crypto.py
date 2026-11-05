"""字段级加密（AES-256-GCM）。

保护的是"数据库或备份泄露"这一层：
即使 dump 被拿走，秘密和日记也读不出来。

注意：这是服务端加密，不是端到端加密。拥有服务器和密钥的人仍然可以解密。

密文格式：
    v1:<base64(nonce + ciphertext + tag)>
前缀 `v1:` 用于将来做密钥轮换时区分版本，也用于识别历史明文。
"""

import base64
import hashlib
import os
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

_PREFIX = "v1:"
# GCM 推荐 96 位 nonce。每个加密操作都必须生成新的随机 nonce，
# 重复使用 nonce 会直接毁掉 GCM 的安全性。
_NONCE_SIZE = 12


@lru_cache(maxsize=4)
def _derive_key(raw: str) -> bytes:
    """把任意长度的配置字符串哈希成 32 字节密钥。

    用 SHA-256 而不是直接截断，保证长度正确且分布均匀。
    加缓存是因为每次读写字段都会调用。
    """
    return hashlib.sha256(raw.encode()).digest()


def _key() -> bytes:
    """取当前生效的密钥。

    生产环境必须显式配置 DATA_ENCRYPTION_KEY；
    开发环境退化为用 JWT_SECRET 派生，保证本地开箱即用。
    """
    raw = settings.DATA_ENCRYPTION_KEY
    if not raw:
        if settings.ENV == "prod":
            raise RuntimeError("生产环境必须配置 DATA_ENCRYPTION_KEY")
        # 开发环境用 JWT_SECRET 派生，保证本地能直接跑
        raw = settings.JWT_SECRET
    return _derive_key(raw)


def ensure_configured() -> None:
    """生产环境启动时检查密钥，避免上线后才发现。

    在 app/main.py 的 lifespan 里调用。
    """
    if settings.ENV == "prod" and not settings.DATA_ENCRYPTION_KEY:
        raise RuntimeError("生产环境必须配置 DATA_ENCRYPTION_KEY")


def encrypt(plaintext: str | None) -> str | None:
    """加密字符串。

    已经是密文（v1: 开头）时原样返回，
    这样重复处理（例如脚本重跑）不会二次加密。
    """
    if plaintext is None:
        return None
    if plaintext.startswith(_PREFIX):
        # 已经是密文，避免重复加密
        return plaintext

    nonce = os.urandom(_NONCE_SIZE)
    ciphertext = AESGCM(_key()).encrypt(nonce, plaintext.encode(), None)
    return _PREFIX + base64.b64encode(nonce + ciphertext).decode()


def decrypt(token: str | None) -> str | None:
    """解密字符串。

    没有 v1: 前缀时当作历史明文原样返回，
    这样上线加密功能后，旧数据不需要立刻迁移也能读。
    """
    if token is None:
        return None
    if not token.startswith(_PREFIX):
        # 兼容历史明文数据
        return token

    raw = base64.b64decode(token[len(_PREFIX) :])
    nonce, ciphertext = raw[:_NONCE_SIZE], raw[_NONCE_SIZE:]
    # 密文被篡改时 GCM 会抛 InvalidTag，而不是返回错误内容
    return AESGCM(_key()).decrypt(nonce, ciphertext, None).decode()
