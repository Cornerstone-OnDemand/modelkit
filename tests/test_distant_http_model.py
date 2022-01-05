import json
import os
import subprocess
import time

import pytest
import requests

from modelkit.core.library import ModelLibrary
from modelkit.core.model import ConcreteMixin
from modelkit.core.models.distant_model import AsyncDistantHTTPModel, DistantHTTPModel
from tests import TEST_DIR


@pytest.fixture(scope="module")
def run_mocked_service():
    proc = subprocess.Popen(
        ["uvicorn", "mocked_service:app"], cwd=os.path.join(TEST_DIR, "testdata")
    )

    done = False
    for _ in range(300):
        try:
            requests.post(
                "http://localhost:8000/api/path/endpoint", data=json.dumps({"ok": "ok"})
            )
            done = True
            break
        except requests.ConnectionError:
            time.sleep(0.01)
    if not done:
        raise Exception("Could not start mocked service")

    yield
    proc.terminate()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "item,params,expected",
    [
        ({"some_content": "something"}, {}, {"some_content": "something"}),
        (
            {"some_content": "something"},
            {"limit": 10},
            {"some_content": "something", "limit": 10},
        ),
        (
            {"some_content": "something"},
            {"skip": 5},
            {"some_content": "something", "skip": 5},
        ),
        (
            {"some_content": "something"},
            {"limit": 10, "skip": 5},
            {"some_content": "something", "limit": 10, "skip": 5},
        ),
    ],
)
async def test_distant_http_model(
    item, params, expected, run_mocked_service, event_loop
):
    async_model_settings = {
        "endpoint": "http://127.0.0.1:8000/api/path/endpoint",
        "async_mode": True,
    }
    sync_model_settings = {
        "endpoint": "http://127.0.0.1:8000/api/path/endpoint",
        "async_mode": False,
    }

    class SomeDistantHTTPModel(ConcreteMixin, DistantHTTPModel):
        CONFIGURATIONS = {
            "some_model_sync": {"model_settings": sync_model_settings},
        }

    class SomeAsyncDistantHTTPModel(ConcreteMixin, AsyncDistantHTTPModel):
        CONFIGURATIONS = {"some_model_async": {"model_settings": async_model_settings}}

    lib_without_params = ModelLibrary(
        models=[SomeDistantHTTPModel, SomeAsyncDistantHTTPModel]
    )
    lib_with_params = ModelLibrary(
        models=[SomeDistantHTTPModel, SomeAsyncDistantHTTPModel],
        configuration={
            "some_model_sync": {
                "model_settings": {**params, **sync_model_settings},
            },
            "some_model_async": {"model_settings": {**params, **async_model_settings}},
        },
    )
    for lib in [lib_without_params, lib_with_params]:
        # Test with asynchronous mode
        m = lib.get("some_model_async")
        with pytest.raises(AssertionError):
            assert expected == m(item, endpoint_params=params)

        res = await m.predict(item, endpoint_params=params)
        assert expected == res
        await lib.aclose()

        # Test with synchronous mode
        m = lib.get("some_model_sync")
        assert expected == m(item, endpoint_params=params)
