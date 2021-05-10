import contextlib
import copy
import os

import structlog
from structlog.testing import capture_logs

from modelkit import logging
from modelkit.logging.context import ContextualizedLogging

test_path = os.path.dirname(os.path.realpath(__file__))


def test_json_logging(monkeypatch):
    monkeypatch.setenv("DEV_LOGGING", "")
    with capture_logs() as cap_logs:
        logger = structlog.get_logger("testing")
        logger.info("It works", even_with="structured fields")
    d = cap_logs[0]
    assert d["even_with"] == "structured fields"
    assert d["event"] == "It works"


TEST_EVENT_DICT = {"event": "info", "logger": "test", "timestamp": "now"}
RES_WITH_COLOR = "\x1b[2mnow\x1b[0m [\x1b[34m\x1b[1mtest\x1b[0m] \x1b[1minfo\x1b[0m"
RES_NO_COLOR = "now [test] info"


def test_renderer_colors():
    renderer = logging.renderer.CustomConsoleRenderer()
    assert renderer(None, None, copy.deepcopy(TEST_EVENT_DICT)) == RES_WITH_COLOR
    assert (
        renderer(None, None, {**copy.deepcopy(TEST_EVENT_DICT), "extra": "value"})
        == RES_WITH_COLOR + "\n\t" + "\x1b[36mextra\x1b[0m=\x1b[35mvalue\x1b[0m"
    )


def test_renderer_no_colors():
    renderer = logging.renderer.CustomConsoleRenderer(colors=False)
    assert renderer(None, None, copy.deepcopy(TEST_EVENT_DICT)) == RES_NO_COLOR
    assert (
        renderer(None, None, {**copy.deepcopy(TEST_EVENT_DICT), "extra": "value"})
        == RES_NO_COLOR + "\n\t" + "extra=value"
    )


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
