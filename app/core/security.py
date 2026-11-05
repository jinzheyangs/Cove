"""密码哈希与 JWT。

职责边界：
- 密码：argon2 哈希，永不存明文
- access token：无状态 JWT，短有效期，用于每次请求鉴权
- refresh token：随机串，存库并可吊销，见 users/service.py
"""

from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

# recommended() 当前选的是 argon2，参数由库根据机器性能自动决定。
# 进程内复用同一个实例，避免每次哈希都重新初始化。
_password_hash = PasswordHash.recommended()


def hash_password(raw: str) -> str:
    """把明文密码哈希成可入库的字符串。"""
    return _password_hash.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    """校验密码。

    历史上库里的值可能不是合法哈希（例如测试数据），
    这里统一吞掉异常当作“验证失败”，避免把 500 暴露给登录接口。
    """
    try:
        return _password_hash.verify(raw, hashed)
    except Exception:  # noqa: BLE001 - 哈希格式异常一律视为验证失败
        return False


def create_access_token(user_id: int) -> str:
    """签发 access token。

    payload 只放最小信息：
    - sub: 用户 id（JWT 规范要求是字符串）
    - iat/exp: 签发时间和过期时间

    不放昵称、手机号等资料，避免 token 泄露时连带泄露隐私。
    """
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> int:
    """校验并解析 access token，返回用户 id。

    签名错误、过期、格式错误都会抛异常，
    由调用方（core/deps.py）统一转换成 401。
    """
    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )
    return int(payload["sub"])
