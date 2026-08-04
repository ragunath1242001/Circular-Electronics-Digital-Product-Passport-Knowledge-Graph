import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    _extra_fields = (
        "request_id",
        "method",
        "path",
        "status_code",
        "duration_ms",
        "validation_run_id",
        "conforms",
        "job_id",
        "action",
        "result",
        "error_category",
    )

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        entry.update(
            (field, getattr(record, field))
            for field in self._extra_fields
            if hasattr(record, field)
        )
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
