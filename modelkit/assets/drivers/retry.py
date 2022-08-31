import requests
from structlog import get_logger
from tenacity import retry_if_exception, stop_after_attempt, wait_random_exponential

logger = get_logger(__name__)


def log_after_retry(retry_state):
    logger.info(
        "Retrying",
        fun=retry_state.fn.__name__,
        attempt_number=retry_state.attempt_number,
        wait_time=retry_state.outcome_timestamp - retry_state.start_time,
    )


def retry_policy(type_error=None):
    if not type_error:

        def is_retry_eligible(error):
            return isinstance(error, requests.exceptions.ChunkedEncodingError)

    else:

        def is_retry_eligible(error):
            return isinstance(error, type_error) or isinstance(
                error, requests.exceptions.ChunkedEncodingError
            )

    return {
        "wait": wait_random_exponential(multiplier=1, min=4, max=10),
        "stop": stop_after_attempt(5),
        "retry": retry_if_exception(is_retry_eligible),
        "after": log_after_retry,
        "reraise": True,
    }
