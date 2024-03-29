from dataclasses import dataclass
from typing import Callable

from structlog import get_logger
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)

logger = get_logger(__name__)
try:
    import redis
except ImportError:  # pragma: no cover
    logger.debug("Redis is not available " "(install modelkit[redis] or redis)")


class RedisCacheException(Exception):
    pass


def log_after_retry(retry_state):
    logger.info(
        "Retrying",
        fun=retry_state.fn.__name__,
        attempt_number=retry_state.attempt_number,
        wait_time=retry_state.outcome_timestamp - retry_state.start_time,
    )


def retriable_error(exception):
    return isinstance(exception, (AssertionError, redis.ConnectionError))


@dataclass
class REDIS_RETRY_POLICY:
    wait: wait_random_exponential = wait_random_exponential(multiplier=1, min=4, max=10)
    stop: stop_after_attempt = stop_after_attempt(5)
    retry: retry_if_exception = retry_if_exception(retriable_error)
    after: Callable = log_after_retry
    reraise: bool = True


@retry(
    wait=REDIS_RETRY_POLICY.wait,
    stop=REDIS_RETRY_POLICY.stop,
    retry=REDIS_RETRY_POLICY.retry,
    after=REDIS_RETRY_POLICY.after,
    reraise=REDIS_RETRY_POLICY.reraise,
)
def connect_redis(host, port):
    redis_cache = redis.Redis(host=host, port=port)
    if not redis_cache.ping():
        raise ConnectionError("Cannot connect to redis")
    return redis_cache
