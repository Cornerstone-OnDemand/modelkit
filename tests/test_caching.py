import asyncio
import os
import subprocess
import time
from typing import List, Union

import pydantic
import pytest
import redis

import modelkit.utils.redis
from modelkit.core.library import ModelLibrary
from modelkit.core.model import AsyncModel, Model
from modelkit.utils.cache import NativeCache, RedisCache
from tests.conftest import skip_unless


@pytest.mark.parametrize("cache_implementation", ["LFU", "LRU", "RR"])
def test_native_cache(cache_implementation):
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

    class Item(pydantic.BaseModel):
        class SubItem(pydantic.BaseModel):
            boomer: Union[int, List[int]]

        ok: SubItem

    class SomeModelValidated(Model[Item, Item]):
        CONFIGURATIONS = {
            "model_validated": {"model_settings": {"cache_predictions": True}}
        }

        def _predict_batch(self, items):
            return items

    lib = ModelLibrary(
        models=[SomeModel, SomeModelMultiple, SomeModelValidated],
        settings={
            "cache": {
                "cache_provider": "native",
                "implementation": cache_implementation,
                "maxsize": 16,
            }
        },
    )

    assert isinstance(lib.cache, NativeCache)

    m = lib.get("model")
    m_multi = lib.get("model_multiple")

    ITEMS = [{"ok": {"boomer": 1}}, {"ok": {"boomer": [2, 2, 3]}}]

    _do_model_test(m, ITEMS)
    _do_model_test(m_multi, ITEMS)

    m_validated = lib.get("model_validated")
    _do_model_test(m_validated, ITEMS)


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
        if isinstance(res, pydantic.BaseModel):
            res = res.model_dump()
        assert i == res

    batch_results = model.predict_batch(ITEMS)
    if isinstance(batch_results[0], pydantic.BaseModel):
        batch_results = [res.model_dump() for res in batch_results]
    assert batch_results == ITEMS

    batch_results = model.predict_batch(ITEMS + [{"ok": {"boomer": [-1]}}])
    if isinstance(batch_results[0], pydantic.BaseModel):
        batch_results = [res.model_dump() for res in batch_results]
    assert batch_results == ITEMS + [{"ok": {"boomer": [-1]}}]


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

    class Item(pydantic.BaseModel):
        class SubItem(pydantic.BaseModel):
            boomer: Union[int, List[int]]

        ok: SubItem

    class SomeModelValidated(Model[Item, Item]):
        CONFIGURATIONS = {
            "model_validated": {"model_settings": {"cache_predictions": True}}
        }

        def _predict_batch(self, items):
            return items

    lib = ModelLibrary(
        models=[SomeModel, SomeModelMultiple, SomeModelValidated],
        settings={"cache": {"cache_provider": "redis"}},
    )

    assert isinstance(lib.cache, RedisCache)

    m = lib.get("model")
    m_multi = lib.get("model_multiple")

    ITEMS = [{"ok": {"boomer": 1}}, {"ok": {"boomer": [2, 2, 3]}}]

    _do_model_test(m, ITEMS)
    _do_model_test(m_multi, ITEMS)

    m_validated = lib.get("model_validated")
    _do_model_test(m_validated, ITEMS)


async def _do_model_test_async(model, ITEMS):
    for i in ITEMS:
        res = await model(i, _force_compute=True)
        if isinstance(res, pydantic.BaseModel):
            res = res.model_dump()
        assert i == res

    res = await model.predict_batch(ITEMS)
    if isinstance(res[0], pydantic.BaseModel):
        res = [item.model_dump() for item in res]
    assert res == ITEMS

    res = await model.predict_batch(ITEMS + [{"ok": {"boomer": [-1]}}])
    if isinstance(res[0], pydantic.BaseModel):
        res = [item.model_dump() for item in res]
    assert ITEMS + [{"ok": {"boomer": [-1]}}] == res


@pytest.mark.asyncio
@skip_unless("ENABLE_REDIS_TEST", "True")
async def test_redis_cache_async(redis_service, event_loop):
    class SomeModel(AsyncModel):
        CONFIGURATIONS = {"model": {"model_settings": {"cache_predictions": True}}}

        async def _predict(self, item):
            await asyncio.sleep(0)
            return item

    class SomeModelMultiple(AsyncModel):
        CONFIGURATIONS = {
            "model_multiple": {"model_settings": {"cache_predictions": True}}
        }

        async def _predict_batch(self, items):
            await asyncio.sleep(0)
            return items

    class Item(pydantic.BaseModel):
        class SubItem(pydantic.BaseModel):
            boomer: Union[int, List[int]]

        ok: SubItem

    class SomeModelValidated(AsyncModel[Item, Item]):
        CONFIGURATIONS = {
            "model_validated": {"model_settings": {"cache_predictions": True}}
        }

        async def _predict_batch(self, items):
            await asyncio.sleep(0)
            return items

    lib = ModelLibrary(
        models=[SomeModel, SomeModelMultiple, SomeModelValidated],
        settings={"cache": {"cache_provider": "redis"}},
    )

    assert isinstance(lib.cache, RedisCache)

    m = lib.get("model")
    m_multi = lib.get("model_multiple")

    ITEMS = [{"ok": {"boomer": 1}}, {"ok": {"boomer": [2, 2, 3]}}]

    await _do_model_test_async(m, ITEMS)
    await _do_model_test_async(m_multi, ITEMS)
    await lib.aclose()

    m_validated = lib.get("model_validated")
    await _do_model_test_async(m_validated, ITEMS)


def test_redis_cache_error(monkeypatch):
    class SomeModelValidated(Model):
        CONFIGURATIONS = {"model": {"model_settings": {"cache_predictions": True}}}

        def _predict_batch(self, items):
            return items

    with pytest.raises(modelkit.utils.redis.RedisCacheException):
        ModelLibrary(
            models=[SomeModelValidated],
            settings={"cache": {"cache_provider": "redis"}},
        )
