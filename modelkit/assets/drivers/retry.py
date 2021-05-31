import botocore
import google
import requests
from structlog import get_logger
from tenacity import retry_if_exception, stop_after_attempt, wait_random_exponential

logger = get_logger(__name__)


def retriable_error(exception):
    return (
        isinstance(exception, botocore.exceptions.ClientError)
        or isinstance(exception, google.api_core.exceptions.GoogleAPIError)
        or isinstance(exception, requests.exceptions.ChunkedEncodingError)
    )


def log_after_retry(retry_state):
    logger.info(
        "Retrying",
        fun=retry_state.fn.__name__,
        attempt_number=retry_state.attempt_number,
        wait_time=retry_state.outcome_timestamp - retry_state.start_time,
    )


RETRY_POLICY = {
    "wait": wait_random_exponential(multiplier=1, min=4, max=10),
    "stop": stop_after_attempt(5),
    "retry": retry_if_exception(retriable_error),
    "after": log_after_retry,
    "reraise": True,
}
