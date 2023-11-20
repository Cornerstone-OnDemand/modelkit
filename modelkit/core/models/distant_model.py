import json
from dataclasses import dataclass
from typing import Callable, Optional

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


@dataclass
class SERVICE_MODEL_RETRY_POLICY:
    wait: wait_random_exponential = wait_random_exponential(multiplier=1, min=4, max=10)
    stop: stop_after_attempt = stop_after_attempt(5)
    retry: retry_if_exception = retry_if_exception(retriable_error)
    after: Callable = log_after_retry
    reraise: bool = True


class AsyncDistantHTTPModel(AsyncModel[ItemType, ReturnType]):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.endpoint = self.model_settings["endpoint"]
        self.endpoint_headers = self.model_settings.get("endpoint_headers", {})
        self.endpoint_params = self.model_settings.get("endpoint_params", {})
        self.aiohttp_session: Optional[aiohttp.ClientSession] = None
        self.timeout = self.model_settings.get("timeout", 60)

    def _load(self):
        pass

    @retry(
        wait=SERVICE_MODEL_RETRY_POLICY.wait,
        stop=SERVICE_MODEL_RETRY_POLICY.stop,
        retry=SERVICE_MODEL_RETRY_POLICY.retry,
        after=SERVICE_MODEL_RETRY_POLICY.after,
        reraise=SERVICE_MODEL_RETRY_POLICY.reraise,
    )
    async def _predict(self, item, **kwargs):
        if self.aiohttp_session is None:
            self.aiohttp_session = aiohttp.ClientSession()
        try:
            item = json.dumps(item)
        except TypeError:
            # TypeError: Object of type {ItemType} is not JSON serializable
            # Try converting the pydantic model to json directly
            item = item.model_dump_json()
        async with self.aiohttp_session.post(
            self.endpoint,
            params=kwargs.get("endpoint_params", self.endpoint_params),
            data=item,
            headers={
                "content-type": "application/json",
                **kwargs.get("endpoint_headers", self.endpoint_headers),
            },
            timeout=self.timeout,
        ) as response:
            if response.status != 200:
                raise DistantHTTPModelError(
                    response.status, response.reason, await response.text()
                )
            return await response.json()

    async def close(self):
        if self.aiohttp_session:
            return self.aiohttp_session.close()


class DistantHTTPModel(Model[ItemType, ReturnType]):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.endpoint = self.model_settings["endpoint"]
        self.endpoint_headers = self.model_settings.get("endpoint_headers", {})
        self.endpoint_params = self.model_settings.get("endpoint_params", {})
        self.requests_session: Optional[requests.Session] = None
        self.timeout = self.model_settings.get("timeout", 60)

    def _load(self):
        pass

    @retry(
        wait=SERVICE_MODEL_RETRY_POLICY.wait,
        stop=SERVICE_MODEL_RETRY_POLICY.stop,
        retry=SERVICE_MODEL_RETRY_POLICY.retry,
        after=SERVICE_MODEL_RETRY_POLICY.after,
        reraise=SERVICE_MODEL_RETRY_POLICY.reraise,
    )
    def _predict(self, item, **kwargs):
        if not self.requests_session:
            self.requests_session = requests.Session()
        try:
            item = json.dumps(item)
        except TypeError:
            # TypeError: Object of type {ItemType} is not JSON serializable
            # Try converting the pydantic model to json directly
            item = item.model_dump_json()
        response = self.requests_session.post(
            self.endpoint,
            params=kwargs.get("endpoint_params", self.endpoint_params),
            data=item,
            headers={
                "content-type": "application/json",
                **kwargs.get("endpoint_headers", self.endpoint_headers),
            },
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise DistantHTTPModelError(
                response.status_code, response.reason, response.text
            )
        return response.json()

    def close(self):
        if self.requests_session:
            return self.requests_session.close()


class DistantHTTPBatchModel(Model[ItemType, ReturnType]):
    """
    Model to extend to be able to call a batch endpoint
    expecting a list of ItemType as input.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.endpoint = self.model_settings["endpoint"]
        self.endpoint_headers = self.model_settings.get("endpoint_headers", {})
        self.endpoint_params = self.model_settings.get("endpoint_params", {})
        self.requests_session: Optional[requests.Session] = None
        self.timeout = self.model_settings.get("timeout", 60)

    def _load(self):
        pass

    @retry(
        wait=SERVICE_MODEL_RETRY_POLICY.wait,
        stop=SERVICE_MODEL_RETRY_POLICY.stop,
        retry=SERVICE_MODEL_RETRY_POLICY.retry,
        after=SERVICE_MODEL_RETRY_POLICY.after,
        reraise=SERVICE_MODEL_RETRY_POLICY.reraise,
    )
    def _predict_batch(self, items, **kwargs):
        if not self.requests_session:
            self.requests_session = requests.Session()
        try:
            items = json.dumps(items)
        except TypeError:
            # TypeError: Object of type {ItemType} is not JSON serializable
            # Try converting a list of pydantic models to dict
            items = json.dumps([item.model_dump() for item in items])
        response = self.requests_session.post(
            self.endpoint,
            params=kwargs.get("endpoint_params", self.endpoint_params),
            data=items,
            headers={
                "content-type": "application/json",
                **kwargs.get("endpoint_headers", self.endpoint_headers),
            },
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise DistantHTTPModelError(
                response.status_code, response.reason, response.text
            )
        return response.json()

    def close(self):
        if self.requests_session:
            return self.requests_session.close()


class AsyncDistantHTTPBatchModel(AsyncModel[ItemType, ReturnType]):
    """
    Async batch model to extend to be able to call a batch endpoint
    expecting a list of ItemType as input.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.endpoint = self.model_settings["endpoint"]
        self.endpoint_headers = self.model_settings.get("endpoint_headers", {})
        self.endpoint_params = self.model_settings.get("endpoint_params", {})
        self.aiohttp_session: Optional[aiohttp.ClientSession] = None
        self.timeout = self.model_settings.get("timeout", 60)

    @retry(
        wait=SERVICE_MODEL_RETRY_POLICY.wait,
        stop=SERVICE_MODEL_RETRY_POLICY.stop,
        retry=SERVICE_MODEL_RETRY_POLICY.retry,
        after=SERVICE_MODEL_RETRY_POLICY.after,
        reraise=SERVICE_MODEL_RETRY_POLICY.reraise,
    )
    async def _predict_batch(self, items, **kwargs):
        if self.aiohttp_session is None:
            self.aiohttp_session = aiohttp.ClientSession()
        try:
            items = json.dumps(items)
        except TypeError:
            # TypeError: Object of type {ItemType} is not JSON serializable
            # Try converting a list of pydantic models to dict
            items = json.dumps([item.model_dump() for item in items])

        async with self.aiohttp_session.post(
            self.endpoint,
            params=kwargs.get("endpoint_params", self.endpoint_params),
            data=items,
            headers={
                "content-type": "application/json",
                **kwargs.get("endpoint_headers", self.endpoint_headers),
            },
            timeout=self.timeout,
        ) as response:
            if response.status != 200:
                raise DistantHTTPModelError(
                    response.status, response.reason, await response.text()
                )
            return await response.json()

    async def close(self):
        if self.aiohttp_session:
            return self.aiohttp_session.close()
