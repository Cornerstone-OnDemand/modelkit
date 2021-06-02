import asyncio
import os
import subprocess
import time

import pytest
import redis

from modelkit.core.library import ModelLibrary
from modelkit.core.model import Model
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


async def _do_model_test(model, ITEMS):
    for i in ITEMS:
        res, from_cache = model(i, _force_compute=True, _return_info=True)
        assert i == res
        assert not from_cache

    for i in ITEMS:
        res, from_cache = model(i, _return_info=True)
        assert i == res
        assert from_cache

    res = model.predict_batch(ITEMS, _return_info=True)
    assert [x[0] for x in res] == ITEMS
    assert all([x[1] for x in res])

    res = await model.predict_batch_async(ITEMS, _return_info=True)
    assert [x[0] for x in res] == ITEMS
    assert all([x[1] for x in res])

    mixed_items = ITEMS + [{"new": "item"}]
    res = model.predict_batch(mixed_items, _return_info=True)
    assert [x[0] for x in res] == mixed_items
    assert all([x[1] for x in res[:-1]])
    assert not res[-1][1]

    mixed_items = ITEMS + [{"new": "item"}]
    res = model.predict_batch(mixed_items, _return_info=True)
    assert [x[0] for x in res] == mixed_items
    assert all([x[1] for x in res])


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

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_do_model_test(m, ITEMS))
    loop.run_until_complete(_do_model_test(m_multi, ITEMS))
    loop.run_until_complete(svc.close_connections())
