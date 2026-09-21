import logging

import structlog

from common.logging import prepare_event
from config.settings.env import LOG_FORMAT, LOG_LEVEL, LOGGING_ENABLED

_SHARED_PROCESSORS = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    prepare_event,
]

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        *_SHARED_PROCESSORS,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "()": structlog.stdlib.ProcessorFormatter,
            "foreign_pre_chain": _SHARED_PROCESSORS,
            "keep_exc_info": False,
            "processors": [
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer() if LOG_FORMAT == "json" else structlog.dev.ConsoleRenderer(),
            ],
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
            "stream": "ext://sys.stdout",
        },
        "null": {"class": "logging.NullHandler"},
    },
    "root": {"handlers": ["console"] if LOGGING_ENABLED else ["null"], "level": LOG_LEVEL},
    "loggers": {
        name: {"handlers": [], "propagate": True, "level": LOG_LEVEL}
        for name in ("django", "django_structlog", "axes", "rest_framework", "silk", "zeal", "py.warnings")
    },
}
# HTTP-события уже пишет middleware; штатные access-логи могут содержать query string.
LOGGING["loggers"]["django.server"] = {"handlers": ["null"], "propagate": False}
LOGGING["loggers"]["django.request"] = {"handlers": ["null"], "propagate": False}
LOGGING["loggers"]["django.db.backends"] = {"handlers": [], "propagate": True, "level": "WARNING"}
# Скрыть информационное сообщение AXES при запуске, сохранив предупреждения.
LOGGING["loggers"]["axes.apps"] = {"handlers": [], "propagate": True, "level": "WARNING"}
DJANGO_STRUCTLOG_IP_LOGGING_ENABLED = False
DJANGO_STRUCTLOG_STATUS_START_LOG_LEVEL = logging.DEBUG
logging.captureWarnings(capture=True)
