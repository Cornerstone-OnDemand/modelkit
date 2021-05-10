import logging
import logging.config
import os
from typing import Any

import structlog
import structlog.contextvars
from structlog import get_logger

from modelkit.logging.renderer import CustomConsoleRenderer

MIN_LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()


def _get_shared_processors(timestamp_fmt):
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt=timestamp_fmt),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]


# Should we log in JSON or not?
processor: Any
if os.environ.get("DEV_LOGGING"):
    shared_processors = _get_shared_processors("%Y-%m-%d %H:%M.%S")
    processor = CustomConsoleRenderer()
else:
    shared_processors = _get_shared_processors("iso")
    processor = structlog.processors.JSONRenderer()

base_stdlib_handler = {"formatter": "main", "level": MIN_LOG_LEVEL}
stdlib_handlers = {
    "default": {
        "class": "logging.StreamHandler",
        "stream": "ext://sys.stdout",
        **base_stdlib_handler,
    }
}

structlog.configure(
    processors=shared_processors
    + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "main": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": processor,
                "foreign_pre_chain": shared_processors,
            },
        },
        "handlers": stdlib_handlers,
        "loggers": {
            "": {
                "handlers": stdlib_handlers.keys(),
                "level": MIN_LOG_LEVEL,
                "propagate": True,
            },
        },
    }
)

__all__ = ("get_logger",)
