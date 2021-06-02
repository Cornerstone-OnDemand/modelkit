import json

import aiohttp
import requests
from structlog import get_logger
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)

from modelkit.core.model import AsyncModel, Model
from modelkit.core.types import ItemType, ReturnType

logger = get_logger(__name__)


class DistantHTTPModelError(Exception):
    def __init__(self, status_code, reason, text):
        super().__init__(f"Service model error [{status_code} {reason}]: {text}")


def log_after_retry(retry_state):
    logger.info(
        "Retrying",
        fun=retry_state.fn.__name__,
        attempt_number=retry_state.attempt_number,
        wait_time=retry_state.outcome_timestamp - retry_state.start_time,
    )


def retriable_error(exception):
    return isinstance(
        exception, aiohttp.client_exceptions.ClientConnectorError
    ) or isinstance(exception, requests.exceptions.ConnectionError)


SERVICE_MODEL_RETRY_POLICY = {
    "wait": wait_random_exponential(multiplier=1, min=4, max=10),
    "stop": stop_after_attempt(5),
    "retry": retry_if_exception(retriable_error),
    "after": log_after_retry,
    "reraise": True,
}


class AsyncDistantHTTPModel(AsyncModel[ItemType, ReturnType]):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.endpoint = self.model_settings["endpoint"]
        self.aiohttp_session = None

    def _load(self):
        pass

    @retry(**SERVICE_MODEL_RETRY_POLICY)
    async def _predict(self, item):
        if self.aiohttp_session is None:
            self.aiohttp_session = aiohttp.ClientSession()
        async with self.aiohttp_session.post(
            self.endpoint,
            data=json.dumps(item),
        ) as response:
            if response.status != 200:
                raise DistantHTTPModelError(
                    response.status, response.reason, await response.text()
                )
            return await response.json()


class DistantHTTPModel(Model[ItemType, ReturnType]):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.endpoint = self.model_settings["endpoint"]
        self.requests_session = None

    def _load(self):
        pass

    @retry(**SERVICE_MODEL_RETRY_POLICY)
    def _predict(self, item):
        if not self.requests_session:
            self.requests_session = requests.Session()
        response = self.requests_session.post(
            self.endpoint,
            data=json.dumps(item),
        )
        if response.status_code != 200:
            raise DistantHTTPModelError(
                response.status_code, response.reason, response.text
            )
        return response.json()
