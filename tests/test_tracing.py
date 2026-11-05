"""链路追踪：默认关闭、开启后能导出 span。"""

from opentelemetry import trace
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.core import tracing
from app.core.config import settings


def test_tracing_disabled_by_default():
    assert settings.OTEL_ENABLED is False


def test_tracing_exports_spans(monkeypatch):
    monkeypatch.setattr(tracing.settings, "OTEL_ENABLED", True)
    exporter = InMemorySpanExporter()

    tracing.setup_tracing(span_exporter=exporter, instrument_clients=False)

    tracer = trace.get_tracer("test")
    with tracer.start_as_current_span("unit-test"):
        pass

    names = [span.name for span in exporter.get_finished_spans()]
    assert "unit-test" in names
