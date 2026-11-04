"""简单熔断器。

只用来保护外部依赖（当前是大模型 API）。
连续失败达到阈值 → 打开，一段时间内直接拒绝；
到期后进入半开，放一个请求试探，成功则关闭，失败则重新打开。
"""

import time

CLOSED = "closed"
OPEN = "open"
HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, *, failure_threshold: int = 5, recovery_timeout: float = 60.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failures = 0
        self._opened_at: float | None = None

    def current_state(self) -> str:
        if self._opened_at is None:
            return CLOSED
        if time.monotonic() - self._opened_at >= self.recovery_timeout:
            return HALF_OPEN
        return OPEN

    def allow_request(self) -> bool:
        return self.current_state() != OPEN

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._opened_at = time.monotonic()
