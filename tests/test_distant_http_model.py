import json
import os
import subprocess
import time

import pytest
import requests

from modelkit.core.library import ModelLibrary
from modelkit.core.models.distant_model import (
    AsyncDistantHTTPModel,
    DistantHTTPModel,
    build_url,
)
from tests import TEST_DIR


@pytest.fixture()
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


async def _check_service_async(model, item):
    res = await model.predict(item)
    assert item == res


@pytest.mark.asyncio
async def test_distant_http_model(run_mocked_service, event_loop):
    class SomeDistantHTTPModel(DistantHTTPModel):
        CONFIGURATIONS = {
            "some_model_sync": {
                "model_settings": {
                    "endpoint": "http://127.0.0.1:8000/api/path/endpoint",
                    "async_mode": False,
                }
            },
        }

    class SomeAsyncDistantHTTPModel(AsyncDistantHTTPModel):
        CONFIGURATIONS = {
            "some_model_async": {
                "model_settings": {
                    "endpoint": "http://127.0.0.1:8000/api/path/endpoint",
                    "async_mode": True,
                }
            }
        }

    lib = ModelLibrary(models=[SomeDistantHTTPModel, SomeAsyncDistantHTTPModel])
    ITEM = {"some_content": "something"}

    # Test with asynchronous mode
    m = lib.get("some_model_async")
    with pytest.raises(AssertionError):
        assert ITEM == m(ITEM)
    await _check_service_async(m, ITEM)
    await lib.aclose()

    # Test with synchronous mode
    m = lib.get("some_model_sync")
    assert ITEM == m(ITEM)


@pytest.mark.parametrize(
    "url,params,expected",
    [
        ("", {}, ""),
        ("", {"param1": "a", "param2": "b"}, "?param1=a&param2=b"),
        ("some_url_without_params", {}, "some_url_without_params"),
        (
            "some_url_with_params",
            {"param1": 10, "param2": 50},
            "some_url_with_params?param1=10&param2=50",
        ),
        (
            "some_url_with_none_params",
            {"param1": None, "param2": None},
            "some_url_with_none_params?param1=None&param2=None",
        ),
    ],
)
def test_build_url(url, params, expected):
    assert build_url(url, params) == expected
