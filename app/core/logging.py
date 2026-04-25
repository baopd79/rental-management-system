"""Structured logging configuration.

Two output modes:
- Development: human-readable colored console
- Staging/Production: JSON for log aggregators
"""

import logging
import sys
from contextvars import ContextVar

import structlog

from app.core.config import get_settings

# Contextvar for request-scoped fields (request_id, user_id, ...)
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def _add_request_id(logger, method_name, event_dict):
    """Processor: inject request_id from contextvar into log entry."""
    request_id = request_id_var.get()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def configure_logging() -> None:
    """Setup structlog. Call once at app startup."""
    settings = get_settings()

    # Set stdlib logging level (uvicorn, sqlalchemy use stdlib)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=settings.log_level,
    )

    # Common processors for both dev and prod
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_request_id,
    ]

    # Final renderer: pretty for dev, JSON for prod
    if settings.app_env == "development":
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None):
    """Get a structured logger. Use module name typically."""
    return structlog.get_logger(name)
