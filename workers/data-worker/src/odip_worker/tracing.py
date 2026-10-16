"""Bounded worker traces exported to the platform's pod-local OTLP forwarder."""

import os
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


def configure():
    """Tracing is enabled only when the platform injects its private endpoint."""
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return None
    if endpoint != "http://127.0.0.1:4318":
        raise ValueError("Unexpected platform trace endpoint")
    rate = float(os.environ.get("OTEL_TRACES_SAMPLER_ARG", "0.1"))
    if not 0 <= rate <= 1:
        raise ValueError("Invalid platform trace sampling rate")
    provider = TracerProvider(
        resource=Resource.create({"service.name": os.environ["OTEL_SERVICE_NAME"]}),
        sampler=ParentBased(TraceIdRatioBased(rate)),
    )
    provider.add_span_processor(BatchSpanProcessor(
        OTLPSpanExporter(endpoint=endpoint + "/v1/traces", timeout=2),
        max_queue_size=256, max_export_batch_size=64, schedule_delay_millis=1000,
    ))
    trace.set_tracer_provider(provider)
    return provider


@contextmanager
def span(name):
    # User data and exception messages must never enter trace attributes or events.
    with trace.get_tracer("odip.worker").start_as_current_span(
        name, record_exception=False, set_status_on_exception=False,
    ) as current:
        yield current


def traceparent_header():
    context = trace.get_current_span().get_span_context()
    if not context.is_valid:
        return {}
    carrier = {}
    TraceContextTextMapPropagator().inject(carrier)
    return {"traceparent": carrier["traceparent"]}
