import json
import logging
import os
import sys
from datetime import datetime, timezone

LOGGER_NAME = "arquila"
STANDARD_FIELDS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {
    "message",
    "asctime",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "time": datetime.fromtimestamp(record.created, timezone.utc).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname.lower(),
            "event": record.getMessage(),
        }
        entry.update(
            {key: value for key, value in record.__dict__.items() if key not in STANDARD_FIELDS}
        )

        if record.exc_info:
            entry["error"] = self.formatException(record.exc_info)

        return json.dumps(entry, ensure_ascii=False, default=str)


def configure_logging() -> logging.Logger:
    configured = logging.getLogger(LOGGER_NAME)

    if not configured.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        configured.addHandler(handler)
        configured.propagate = False

    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    configured.setLevel(level if level in logging.getLevelNamesMapping() else "INFO")

    return configured


logger = configure_logging()
