import os
import subprocess
import time

import pytest
import redis

from modelkit.core.library import ModelLibrary
from modelkit.core.model import AsyncModel, Model
from tests.conftest import skip_unless


@pytest.fixture()
def redis_service(request):
    if "JENKINS_CI" in os.environ:
        redis_proc = subprocess.Popen(["redis-server"])

        def finalize():
            redis_proc.terminate()

    else:
        # start redis as docker container
        subprocess.Popen(
            ["docker", "run", "--name", "redis-tests", "-p", "6379:6379", "redis:5"]
        )

        def finalize():
            subprocess.call(["docker", "rm", "-f", "redis-tests"])

    request.addfinalizer(finalize)
    rd = redis.Redis(host="localhost", port=6379)
    for _ in range(30):
        try:
            if rd.ping():
                break
        except redis.ConnectionError:
            time.sleep(1)
    yield


def _do_model_test(model, ITEMS):
    for i in ITEMS:
        res = model(i, _force_compute=True)
        assert i == res

    assert model.predict_batch(ITEMS) == ITEMS

    assert ITEMS + [{"new": "item"}] == model.predict_batch(ITEMS + [{"new": "item"}])


@skip_unless("ENABLE_REDIS_TEST", "True")
def test_redis_cache(redis_service):
    class SomeModel(Model):
        CONFIGURATIONS = {"model": {"model_settings": {"cache_predictions": True}}}

        def _predict(self, item):
            return item

    class SomeModelMultiple(Model):
        CONFIGURATIONS = {
            "model_multiple": {"model_settings": {"cache_predictions": True}}
        }

        def _predict_batch(self, items):
            return items

    svc = ModelLibrary(
        models=[SomeModel, SomeModelMultiple],
        settings={"redis": {"enable": True}},
    )

    m = svc.get("model")
    m_multi = svc.get("model_multiple")

    ITEMS = [{"ok": {"boomer": 1}}, {"ok": {"boomer": [2, 2, 3]}}]

    _do_model_test(m, ITEMS)
    _do_model_test(m_multi, ITEMS)


async def _do_model_test_async(model, ITEMS):
    for i in ITEMS:
        res = await model(i, _force_compute=True)
        assert i == res

    res = await model.predict_batch(ITEMS)
    assert res == ITEMS

    res = await model.predict_batch(ITEMS + [{"new": "item"}])
    assert ITEMS + [{"new": "item"}] == res


@pytest.mark.asyncio
@skip_unless("ENABLE_REDIS_TEST", "True")
async def test_redis_cache_async(redis_service, event_loop):
    class SomeModel(AsyncModel):
        CONFIGURATIONS = {"model": {"model_settings": {"cache_predictions": True}}}

        async def _predict(self, item):
            return item

    class SomeModelMultiple(AsyncModel):
        CONFIGURATIONS = {
            "model_multiple": {"model_settings": {"cache_predictions": True}}
        }

        async def _predict_batch(self, items):
            return items

    svc = ModelLibrary(
        models=[SomeModel, SomeModelMultiple],
        settings={"redis": {"enable": True}},
    )

    m = svc.get("model")
    m_multi = svc.get("model_multiple")

    ITEMS = [{"ok": {"boomer": 1}}, {"ok": {"boomer": [2, 2, 3]}}]

    await _do_model_test_async(m, ITEMS)
    await _do_model_test_async(m_multi, ITEMS)
    await svc.close_connections()
