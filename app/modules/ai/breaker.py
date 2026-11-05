"""简单熔断器。

只用来保护外部依赖（当前是大模型 API）。

状态机：
    closed --连续失败达到阈值--> open --等待 recovery_timeout--> half_open
    half_open --成功--> closed
    half_open --失败--> open（重新计时）

为什么需要：
模型服务超时或 5xx 时，继续请求只会让用户等更久、让账单更高。
熔断后直接返回降级结果，把恢复时间留给上游。
"""

import time

CLOSED = "closed"
OPEN = "open"
HALF_OPEN = "half_open"


class CircuitBreaker:
    """进程内熔断器。

    注意：状态存在进程内存里，多实例部署时每个实例各算各的。
    对当前规模够用；如果以后要全局一致，可以把计数放到 Redis。
    """

    def __init__(self, *, failure_threshold: int = 5, recovery_timeout: float = 60.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failures = 0
        self._opened_at: float | None = None

    def current_state(self) -> str:
        """返回当前状态。

        用 monotonic 而不是 wall clock：
        系统时间被调整时不会影响熔断窗口。
        """
        if self._opened_at is None:
            return CLOSED
        if time.monotonic() - self._opened_at >= self.recovery_timeout:
            # 到期后进入半开：允许一个请求去试探
            return HALF_OPEN
        return OPEN

    def allow_request(self) -> bool:
        """open 时拒绝，closed / half_open 时放行。"""
        return self.current_state() != OPEN

    def record_success(self) -> None:
        """成功：清零失败计数并关闭熔断。"""
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        """失败：累计到阈值后打开熔断。

        半开状态下失败会重新打开，因为 _failures 仍然 >= 阈值。
        """
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._opened_at = time.monotonic()
