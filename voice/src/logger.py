"""
JARVIS Voice Layer — Logging setup
Structured JSON logging or human-readable depending on config.
"""

import logging
import json
import time
from typing import Any

from . import config


class _JsonFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log: dict[str, Any] = {
            "timestamp": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log["exc_info"] = self.formatException(record.exc_info)
        # Merge any extra fields passed via extra={...}
        for key, value in record.__dict__.items():
            if key.startswith("_jarvis_"):
                log[key[8:]] = value
        return json.dumps(log)


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for the given module name."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already set up

    logger.setLevel(getattr(logging, config.LOG_LEVEL, logging.INFO))
    handler = logging.StreamHandler()

    if config.LOG_JSON:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            )
        )
    logger.addHandler(handler)
    logger.propagate = False
    return logger
