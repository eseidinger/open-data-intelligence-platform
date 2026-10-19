"""Single-line JSON console logging for the worker and its libraries."""

from datetime import datetime, timezone
import json
import logging
import sys


class JsonFormatter(logging.Formatter):
    def format(self, record):
        document = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("event", "error_type"):
            if hasattr(record, field):
                document[field] = getattr(record, field)
        # Exception messages and tracebacks can contain source URLs or credentials.
        if record.exc_info:
            document["error_type"] = record.exc_info[0].__name__
        return json.dumps(document, separators=(",", ":"))


def configure_logging():
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
