"""OpenTelemetry 链路追踪。

默认关闭。设置 OTEL_ENABLED=true 后：
- FastAPI / SQLAlchemy / Redis / httpx 自动打点
- 通过 OTLP HTTP 导出到 Jaeger 或 Collector
- httpx 打点会顺带覆盖 OpenAI SDK 的模型调用
"""

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
    SpanExporter,
)
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

from app.core.config import settings

logger = structlog.get_logger("tracing")


def setup_tracing(
    app=None,
    engine=None,
    *,
    span_exporter: SpanExporter | None = None,
    instrument_clients: bool = True,
) -> None:
    if not settings.OTEL_ENABLED:
        return

    resource = Resource.create(
        {
            "service.name": settings.OTEL_SERVICE_NAME,
            "service.version": "0.1.0",
            "deployment.environment": settings.ENV,
        }
    )
    provider = TracerProvider(
        resource=resource,
        sampler=ParentBased(TraceIdRatioBased(settings.OTEL_SAMPLE_RATIO)),
    )

    if span_exporter is not None:
        # 测试注入用：同步导出，避免后台线程
        provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    else:
        provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_ENDPOINT)
            )
        )

    trace.set_tracer_provider(provider)

    if app is not None:
        FastAPIInstrumentor.instrument_app(
            app, excluded_urls="health,health/db,metrics"
        )

    if engine is not None:
        SQLAlchemyInstrumentor().instrument(
            engine=engine.sync_engine, enable_commenter=True
        )

    if instrument_clients:
        RedisInstrumentor().instrument()
        HTTPXClientInstrumentor().instrument()

    logger.info(
        "tracing.enabled",
        endpoint=settings.OTEL_EXPORTER_ENDPOINT,
        sample_ratio=settings.OTEL_SAMPLE_RATIO,
    )
