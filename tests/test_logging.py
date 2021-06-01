import contextlib
import os

import structlog
from structlog.testing import capture_logs

from modelkit.utils.logging import ContextualizedLogging

test_path = os.path.dirname(os.path.realpath(__file__))


def test_json_logging(monkeypatch):
    monkeypatch.setenv("DEV_LOGGING", "")
    with capture_logs() as cap_logs:
        logger = structlog.get_logger("testing")
        logger.info("It works", even_with="structured fields")
    d = cap_logs[0]
    assert d["even_with"] == "structured fields"
    assert d["event"] == "It works"


CONTEXT_RES = [
    {
        "context0": "value0",
        "event": "context0 message",
        "log_level": "info",
        "context": "value",
    },
    {
        "context0": "value0override",
        "event": "override context0 message",
        "log_level": "info",
        "context": "value",
    },
    {
        "context0": "value0",
        "context1": "value1",
        "extra_value": 1,
        "event": "context1 message",
        "log_level": "info",
        "context": "value",
    },
    {
        "context0": "value0",
        "event": "context0 message2",
        "log_level": "info",
        "context": "value",
    },
]


@contextlib.contextmanager
def capture_logs_with_contextvars():
    cap = structlog.testing.LogCapture()
    old_processors = structlog.get_config()["processors"]
    try:
        structlog.configure(processors=[structlog.contextvars.merge_contextvars, cap])
        yield cap.entries
    finally:
        structlog.configure(processors=old_processors)


def test_json_context():
    with capture_logs_with_contextvars() as cap_logs:
        logger = structlog.get_logger("testing")
        with ContextualizedLogging(context0="value0", context="value"):
            logger.info("context0 message")
            with ContextualizedLogging(context0="value0override"):
                logger.info("override context0 message")
            with ContextualizedLogging(context1="value1"):
                logger.info("context1 message", extra_value=1)
            logger.info("context0 message2")
    assert cap_logs == CONTEXT_RES
