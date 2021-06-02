import asyncio

import pytest

from modelkit.core.library import ModelLibrary
from modelkit.core.model import AsyncModel, Model


def test_compose_sync_async():
    class SomeAsyncModel(AsyncModel):
        CONFIGURATIONS = {"async_model": {}}

        async def _predict(self, item, **kwargs):
            await asyncio.sleep(0.1)
            return item

    class ComposedModel(Model):
        CONFIGURATIONS = {"composed_model": {"model_dependencies": {"async_model"}}}

        def _predict(self, item, **kwargs):
            return self.model_dependencies["async_model"].predict(item)

    library = ModelLibrary(models=[SomeAsyncModel, ComposedModel])
    m = library.get("composed_model")
    assert m.predict({"hello": "world"}) == {"hello": "world"}


async def _do_async(model, item):
    res = await model.predict(item)
    assert item == res

    res = await model.predict_batch([item] * 10)
    assert [item] * 10 == res


def test_async_predict():
    class SomeModel(AsyncModel):
        async def _predict(self, item, **kwargs):
            await asyncio.sleep(0.1)
            return item

    m = SomeModel()
    with pytest.raises(AssertionError):
        assert m.predict({}) == {}
    with pytest.raises(AssertionError):
        assert m.predict_batch([{}]) == [{}]

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_do_async(m, {}))
