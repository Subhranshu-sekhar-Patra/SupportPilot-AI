"""
SupportPilot AI — Application Logging
Provides a structured logger using standard library logging,
with optional structlog integration if installed.
"""

import logging
import sys
from typing import Any


class AppLogger:
    """Standard logging wrapper providing structured-style key-value logging."""

    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def _format_msg(self, event: str, **kwargs: Any) -> str:
        if kwargs:
            kv_pairs = " ".join(f"{k}={v!r}" for k, v in kwargs.items())
            return f"{event} | {kv_pairs}"
        return event

    def info(self, event: str, **kwargs: Any) -> None:
        self._logger.info(self._format_msg(event, **kwargs))

    def warning(self, event: str, **kwargs: Any) -> None:
        self._logger.warning(self._format_msg(event, **kwargs))

    def error(self, event: str, **kwargs: Any) -> None:
        self._logger.error(self._format_msg(event, **kwargs))

    def debug(self, event: str, **kwargs: Any) -> None:
        self._logger.debug(self._format_msg(event, **kwargs))

    def exception(self, event: str, **kwargs: Any) -> None:
        self._logger.exception(self._format_msg(event, **kwargs))


# Configure root logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def get_logger(name: str = "supportpilot") -> AppLogger:
    return AppLogger(logging.getLogger(name))
