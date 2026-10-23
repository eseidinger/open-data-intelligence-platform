import json
import logging
import os
import subprocess
import sys
import unittest

from odip_worker.logging import JsonFormatter
from opentelemetry import trace
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags


class JsonLoggingTests(unittest.TestCase):
    def test_multiline_library_message_is_one_json_line(self):
        record = logging.LogRecord(
            "opentelemetry.exporter",
            logging.WARNING,
            __file__,
            1,
            "Export failed\nretry %s",
            (2,),
            None,
        )
        output = JsonFormatter().format(record)
        self.assertEqual(len(output.splitlines()), 1)
        event = json.loads(output)
        self.assertEqual(event["message"], "Export failed\nretry 2")
        self.assertEqual(event["level"], "warning")
        self.assertEqual(event["logger"], "opentelemetry.exporter")

    def test_installed_entry_point_reports_failure_without_traceback_or_secrets(self):
        result = self.worker('raise RuntimeError("private-token-value")')
        self.assertEqual(result.returncode, 1)
        events = [json.loads(line) for line in result.stderr.splitlines()]
        self.assertEqual(events[-1]["event"], "job.failed")
        self.assertEqual(events[-1]["error_type"], "RuntimeError")
        self.assertNotIn("private-token-value", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_successful_entry_point_emits_json_lifecycle_and_library_logs(self):
        result = self.worker('logging.getLogger("urllib3").warning("library message")')
        self.assertEqual(result.returncode, 0, result.stderr)
        events = [json.loads(line) for line in result.stderr.splitlines()]
        self.assertEqual(
            [event.get("event") for event in events],
            ["job.started", None, "job.completed"],
        )
        self.assertEqual(events[1]["message"], "library message")

    def test_run_fields_and_active_trace_are_correlated_without_exception_details(self):
        context = SpanContext(
            trace_id=1,
            span_id=2,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )
        try:
            raise ValueError("private-token-value")
        except ValueError:
            record = logging.LogRecord(
                "worker",
                logging.ERROR,
                __file__,
                1,
                "Ingestion failed",
                (),
                sys.exc_info(),
            )
        record.event = "ingestion.failed"
        record.run_id = "12345678-1234-1234-1234-123456789abc"
        record.duration_ms = 12
        with trace.use_span(NonRecordingSpan(context)):
            output = JsonFormatter().format(record)
        event = json.loads(output)
        self.assertEqual(event["trace_id"], "00000000000000000000000000000001")
        self.assertEqual(event["span_id"], "0000000000000002")
        self.assertEqual(event["run_id"], record.run_id)
        self.assertEqual(event["duration_ms"], 12)
        self.assertEqual(event["error_type"], "ValueError")
        self.assertNotIn("private-token-value", output)
        self.assertNotIn("trace_id", json.loads(JsonFormatter().format(record)))

    @staticmethod
    def worker(body):
        # Exercise the same main function as the generated odip-ingest entry point.
        code = (
            "import logging\nfrom unittest.mock import patch\n"
            "from odip_worker.run import main\n"
            "def run():\n    " + body + "\n"
            'with patch("odip_worker.run.run", run):\n    main()\n'
        )
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("OTEL_")
        }
        return subprocess.run(
            [sys.executable, "-c", code],
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
        )
