"""
VIDUR Core Configuration
Module: Core Configuration
Submodule: Logging
Purpose: Structured, production-ready logging configuration for VIDUR.
"""

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict

from app.config.settings import settings


class JSONLogFormatter(logging.Formatter):
    """Formats log records as single-line JSON for production log
    aggregation (e.g. ELK, CloudWatch, Loki)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        project_id = getattr(record, "project_id", None)
        if project_id is not None:
            payload["project_id"] = project_id

        return json.dumps(payload, default=str)


class TextLogFormatter(logging.Formatter):
    """Human-readable formatter for local development."""

    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def configure_logging() -> None:
    """Configure the root VIDUR logger.

    Call once at application startup. Idempotent: safe to call multiple
    times without duplicating handlers.
    """
    root_logger = logging.getLogger("vidur")
    if root_logger.handlers:
        return

    root_logger.setLevel(settings.LOG_LEVEL)
    root_logger.propagate = False

    formatter: logging.Formatter = (
        JSONLogFormatter() if settings.LOG_FORMAT == "json" else TextLogFormatter()
    )

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    os.makedirs(settings.LOG_DIR, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(settings.LOG_DIR, "vidur.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced child logger under the `vidur` root logger."""
    configure_logging()
    return logging.getLogger(f"vidur.{name}")
