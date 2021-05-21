import asyncio
import json
import os
import subprocess
import time

import pytest
import requests

from modelkit.core.library import ModelLibrary
from modelkit.core.models.distant_model import DistantHTTPModel
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
    res = await model.predict_async(item)
    assert item == res


@pytest.mark.asyncio
def test_distant_http_model(run_mocked_service):
    class SomeDistantHTTPModel(DistantHTTPModel):
        CONFIGURATIONS = {
            "some_model": {
                "model_settings": {
                    "endpoint": "http://127.0.0.1:8000/api/path/endpoint"
                }
            },
            "some_model_async": {
                "model_settings": {
                    "endpoint": "http://127.0.0.1:8000/api/path/endpoint",
                    "async_mode": True,
                }
            },
            "some_model_sync": {
                "model_settings": {
                    "endpoint": "http://127.0.0.1:8000/api/path/endpoint",
                    "async_mode": False,
                }
            },
        }

    svc = ModelLibrary(models=SomeDistantHTTPModel)
    ITEM = {"some_content": "something"}
    loop = asyncio.get_event_loop()

    # Test with automatic detection of asynchronous mode
    m = svc.get_model("some_model")
    assert m._async_mode is None
    assert ITEM == m.predict(ITEM)
    loop.run_until_complete(_check_service_async(m, ITEM))
    loop.run_until_complete(svc.close_connections())

    # Test with forced asynchronous mode
    m = svc.get_model("some_model_async")
    assert m._async_mode
    with pytest.raises(RuntimeError):
        assert ITEM == m.predict(ITEM)
    loop.run_until_complete(_check_service_async(m, ITEM))
    loop.run_until_complete(svc.close_connections())

    # Test with forced synchronous mode
    m = svc.get_model("some_model_sync")
    assert m._async_mode is False
    assert ITEM == m.predict(ITEM)
    loop.run_until_complete(_check_service_async(m, ITEM))
    loop.run_until_complete(svc.close_connections())
