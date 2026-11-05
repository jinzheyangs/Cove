"""基于 Redis 有序集合的滑动窗口限流。

为什么不用固定窗口：
固定窗口在边界处会放过最多 2 倍流量——窗口末尾一批 + 下个窗口开头一批
可能同时被允许。滑动窗口始终只统计“最近 window 秒”内的请求，没有这个漏洞。

实现：
- 每个 key 对应一个 ZSET，score 是请求到达时间
- 每次请求先删掉窗口外的成员，再统计数量
- “检查 + 写入”放在一个 Lua 脚本里执行，保证原子性
  （分两步做的话，并发请求会同时通过检查）

时间统一用 Redis 的 TIME，而不是应用服务器时钟：
多实例部署时避免机器之间时钟偏差导致窗口不一致。

设计原则：Redis 不可用时**放行**（fail open）。
限流是为了防滥用，不应该因为缓存挂了把整个服务拖死。
"""

from uuid import uuid4

import structlog
from redis.asyncio import Redis

from app.core.config import settings
from app.core.redis import get_redis

logger = structlog.get_logger("ratelimit")

# KEYS[1] = 限流 key
# ARGV[1] = 上限次数
# ARGV[2] = 窗口秒数
# ARGV[3] = 本次请求的唯一成员（同一毫秒的多个请求也不会互相覆盖）
_HIT_SCRIPT = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local member = ARGV[3]

local t = redis.call('TIME')
local now = tonumber(t[1]) + tonumber(t[2]) / 1000000

-- 移除窗口外的历史请求
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)

-- 先判断再加，整个过程在脚本里原子执行
local count = redis.call('ZCARD', key)
if count < limit then
    redis.call('ZADD', key, now, member)
    -- 过期时间略大于窗口，保证 key 最终会被回收
    redis.call('PEXPIRE', key, math.ceil(window * 1000) + 1000)
    return 1
end
return 0
"""

# KEYS[1] = 限流 key
# ARGV[1] = 窗口秒数
_COUNT_SCRIPT = """
local key = KEYS[1]
local window = tonumber(ARGV[1])

local t = redis.call('TIME')
local now = tonumber(t[1]) + tonumber(t[2]) / 1000000

redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
return redis.call('ZCARD', key)
"""


class RateLimiter:
    """滑动窗口限流器。

    传入 client 而不是在内部创建，方便测试时注入。
    脚本对象在构造时注册，调用时走 EVALSHA，不会每次传整段 Lua。
    """

    def __init__(self, client: Redis) -> None:
        self.client = client
        self._hit_script = client.register_script(_HIT_SCRIPT)
        self._count_script = client.register_script(_COUNT_SCRIPT)

    async def hit(self, key: str, limit: int, window: int) -> bool:
        """记录一次请求，并判断是否仍在额度内。

        Returns:
            True 表示放行，False 表示超限。

        超限时**不会**写入成员：
        否则被拒绝的请求也会占用窗口，形成“越试越封”的雪崩。
        """
        if not settings.RATE_LIMIT_ENABLED:
            return True
        try:
            result = await self._hit_script(
                keys=[key], args=[limit, window, uuid4().hex]
            )
            return bool(result)
        except Exception as exc:  # noqa: BLE001 - 缓存故障不应影响业务
            # fail open：记录告警，但放行
            logger.warning("ratelimit.unavailable", error=repr(exc))
            return True

    async def count(self, key: str, window: int) -> int:
        """统计最近 window 秒内的请求数，不写入新记录。

        登录失败锁定时用它先检查，避免每次登录都白白占一个名额。
        """
        if not settings.RATE_LIMIT_ENABLED:
            return 0
        try:
            result = await self._count_script(keys=[key], args=[window])
            return int(result)
        except Exception as exc:  # noqa: BLE001
            logger.warning("ratelimit.unavailable", error=repr(exc))
            return 0

    async def reset(self, key: str) -> None:
        """清空整个窗口。登录成功后调用，把失败次数归零。"""
        if not settings.RATE_LIMIT_ENABLED:
            return
        try:
            await self.client.delete(key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("ratelimit.unavailable", error=repr(exc))


def get_limiter() -> RateLimiter:
    """每次返回轻量包装对象，底层 Redis 客户端是全局复用的。"""
    return RateLimiter(get_redis())
