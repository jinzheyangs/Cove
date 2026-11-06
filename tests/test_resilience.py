"""可观测性与容错：请求 ID、熔断状态机、AI 降级。"""

import time

import httpx
import pytest

from app.core.errors import AppError
from app.main import app
from app.modules.ai import client as ai_client
from app.modules.ai.breaker import CLOSED, HALF_OPEN, OPEN, CircuitBreaker
from app.modules.simta import service as simta_service
from tests.helpers import seed_couple


async def test_request_id_generated_and_echoed():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        generated = await client.get("/health")
        echoed = await client.get("/health", headers={"X-Request-ID": "trace-123"})

    assert generated.headers.get("X-Request-ID")
    assert echoed.headers["X-Request-ID"] == "trace-123"


def test_breaker_opens_at_threshold():
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=60)
    assert breaker.current_state() == CLOSED

    breaker.record_failure()
    assert breaker.allow_request()

    breaker.record_failure()
    assert breaker.current_state() == OPEN
    assert not breaker.allow_request()


def test_breaker_half_opens_then_closes():
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
    breaker.record_failure()
    assert breaker.current_state() == OPEN

    time.sleep(0.02)
    assert breaker.current_state() == HALF_OPEN
    assert breaker.allow_request()

    breaker.record_success()
    assert breaker.current_state() == CLOSED


async def test_simta_degrades_when_ai_unavailable(session, monkeypatch):
    a, b, couple = await seed_couple(session)
    await simta_service.set_consent(session, couple, b, True)

    async def boom(*, system: str, user: str) -> str:
        raise AppError("AI 服务暂时不可用", code=11003, status_code=503)

    monkeypatch.setattr(ai_client, "complete", boom)

    with pytest.raises(AppError) as exc:
        await simta_service.chat(session, couple, a, "在吗")

    assert exc.value.code == 14002
