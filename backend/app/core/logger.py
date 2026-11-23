"""
SupportPilot AI — Application Logging
Provides a structured logger supporting both key-value text in development
and machine-readable JSON in production environments.
"""

from datetime import datetime, timezone
import json
import logging
import os
import sys
from typing import Any


class AppLogger:
    """Standard logging wrapper providing structured JSON or key-value logging."""

    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def _format_msg(self, level: str, event: str, **kwargs: Any) -> str:
        log_format = os.getenv("LOG_FORMAT", "").lower()
        app_env = os.getenv("APP_ENV", "development").lower()

        if log_format == "json" or app_env == "production":
            data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": level,
                "logger": self._logger.name,
                "event": event,
                **kwargs,
            }
            return json.dumps(data, default=str)

        if kwargs:
            kv_pairs = " ".join(f"{k}={v!r}" for k, v in kwargs.items())
            return f"{event} | {kv_pairs}"
        return event

    def info(self, event: str, **kwargs: Any) -> None:
        self._logger.info(self._format_msg("INFO", event, **kwargs))

    def warning(self, event: str, **kwargs: Any) -> None:
        self._logger.warning(self._format_msg("WARNING", event, **kwargs))

    def error(self, event: str, **kwargs: Any) -> None:
        self._logger.error(self._format_msg("ERROR", event, **kwargs))

    def debug(self, event: str, **kwargs: Any) -> None:
        self._logger.debug(self._format_msg("DEBUG", event, **kwargs))

    def exception(self, event: str, **kwargs: Any) -> None:
        self._logger.exception(self._format_msg("ERROR", event, **kwargs))


# Configure root logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def get_logger(name: str = "supportpilot") -> AppLogger:
    return AppLogger(logging.getLogger(name))
