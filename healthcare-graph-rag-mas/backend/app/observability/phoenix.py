from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from opentelemetry import trace
from opentelemetry.trace import Span

from app.core.settings import Settings

_tracer: trace.Tracer | None = None


def get_tracer() -> trace.Tracer:
    """Return the shared application tracer for manual span creation."""
    global _tracer
    if _tracer is None:
        _tracer = trace.get_tracer("healthcare-graph-rag-mas")
    return _tracer


@contextmanager
def node_span(name: str, attributes: dict | None = None) -> Generator[Span, None, None]:
    """Context manager that wraps a graph node in an OpenTelemetry span."""
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as span:
        span.set_attribute("openinference.span.kind", "CHAIN")
        span.set_attribute("node.name", name)
        if attributes:
            for key, value in attributes.items():
                try:
                    span.set_attribute(key, value)
                except Exception:
                    pass
        yield span


def configure_phoenix(settings: Settings) -> None:
    """Configure Phoenix tracing when the optional runtime package is available."""
    if not settings.phoenix_collector_endpoint:
        return
    try:
        from phoenix.otel import register

        traces_endpoint = f"{settings.phoenix_collector_endpoint.rstrip('/')}/v1/traces"
        register(project_name="healthcare-graph-rag-mas", endpoint=traces_endpoint)

        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        HTTPXClientInstrumentor().instrument()
    except Exception:
        # Observability should never block briefing generation in the prototype.
        return

    # LangChain / LangGraph auto-instrumentation (optional dependency)
    try:
        from opentelemetry.instrumentation.langchain import LangChainInstrumentor
        LangChainInstrumentor().instrument()
    except Exception:
        pass

