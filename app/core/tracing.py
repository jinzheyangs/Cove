"""OpenTelemetry 链路追踪。

默认关闭。设置 OTEL_ENABLED=true 后：
- FastAPI / SQLAlchemy / Redis / httpx 自动打点
- 通过 OTLP HTTP 导出到 Jaeger 或 Collector
- httpx 打点会顺带覆盖 OpenAI SDK 的模型调用

为什么默认关闭：
测试和本地开发不需要 Jaeger，强制依赖会让环境变重。
生产环境按需打开，采样率可以调低。
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
    """初始化追踪。OTEL_ENABLED=false 时直接返回，零开销。

    Args:
        app: FastAPI 实例。传了才会自动给路由打点。
        engine: SQLAlchemy AsyncEngine。传了才会记录 SQL span。
        span_exporter: 仅测试用。传入后改用同步导出，避免后台线程。
        instrument_clients: 是否给 Redis / httpx 打点。
            测试里关掉，避免污染其他用例的 HTTP 客户端。

    注意：`trace.set_tracer_provider` 每个进程只能生效一次，
    重复调用会被忽略并打印警告。因此这个方法只在启动时调用一次。
    """
    if not settings.OTEL_ENABLED:
        return

    # service.name 是 Jaeger 里区分服务的依据
    resource = Resource.create(
        {
            "service.name": settings.OTEL_SERVICE_NAME,
            "service.version": "0.1.0",
            "deployment.environment": settings.ENV,
        }
    )
    # ParentBased：如果上游传了采样决定就沿用，避免上下游采样不一致
    provider = TracerProvider(
        resource=resource,
        sampler=ParentBased(TraceIdRatioBased(settings.OTEL_SAMPLE_RATIO)),
    )

    if span_exporter is not None:
        # 测试注入用：同步导出，避免后台线程
        provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    else:
        # 生产用批量导出：攒一批再发，减少网络开销
        provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_ENDPOINT)
            )
        )

    trace.set_tracer_provider(provider)

    if app is not None:
        # 健康和指标接口量大且无排障价值，排除掉避免噪音
        FastAPIInstrumentor.instrument_app(
            app, excluded_urls="health,health/db,metrics"
        )

    if engine is not None:
        # 异步引擎要传 sync_engine，插桩实际作用在底层的同步引擎上
        # enable_commenter=True 会把 SQL 文本带进 span tag，方便定位慢查询
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
