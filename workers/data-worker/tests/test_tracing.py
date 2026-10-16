import unittest
from unittest.mock import Mock, patch

from opentelemetry import trace
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags, TraceState

from odip_worker.auth import call
from odip_worker.tracing import configure, traceparent_header


class TracingTests(unittest.TestCase):
    def test_only_traceparent_is_forwarded_to_api(self):
        context = SpanContext(
            trace_id=0x11111111111111111111111111111111,
            span_id=0x2222222222222222,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
            trace_state=TraceState(),
        )
        with patch.dict("os.environ", {"ODIP_IDENTITY_MODE": "development"}), \
                trace.use_span(NonRecordingSpan(context)), \
                patch("odip_worker.auth.requests.get", return_value=Mock(status_code=200)) as get:
            call("get", "http://localhost:8080/api/pipeline-runs/claim-next")
        headers = get.call_args.kwargs["headers"]
        self.assertEqual(headers["traceparent"],
                         "00-11111111111111111111111111111111-2222222222222222-01")
        self.assertNotIn("baggage", headers)
        self.assertNotIn("tracestate", headers)

    def test_disabled_without_platform_endpoint(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(configure())
            self.assertEqual(traceparent_header(), {})

    def test_rejects_nonlocal_export_endpoint(self):
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://example.test:4318"}):
            with self.assertRaisesRegex(ValueError, "Unexpected platform trace endpoint"):
                configure()
