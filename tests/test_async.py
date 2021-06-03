import asyncio

import pydantic
import pytest

from modelkit.core.library import ModelLibrary
from modelkit.core.model import AsyncModel, Model, WrappedAsyncModel


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
    assert isinstance(m.model_dependencies["async_model"], WrappedAsyncModel)
    assert m.predict({"hello": "world"}) == {"hello": "world"}


async def _do_async(model, item, expected=None):
    expected = expected or item
    res = await model.predict(item)
    assert expected == res

    res = await model.predict_batch([item] * 10)
    assert [expected] * 10 == res


@pytest.mark.asyncio
async def test_async_predict(event_loop):
    class SomeModel(AsyncModel):
        async def _predict(self, item, **kwargs):
            await asyncio.sleep(0.1)
            return item

    m = SomeModel()
    with pytest.raises(AssertionError):
        assert m.predict({}) == {}
    with pytest.raises(AssertionError):
        assert m.predict_batch([{}]) == [{}]

    await _do_async(m, {})

    class Item(pydantic.BaseModel):
        x: int

    class SomeModel(AsyncModel[Item, Item]):
        async def _predict(self, item, **kwargs):
            await asyncio.sleep(0.1)
            return item

    m = SomeModel()
    with pytest.raises(AssertionError):
        assert m.predict({"x": 1}) == Item(x=1)
    with pytest.raises(AssertionError):
        assert m.predict_batch([{"x": 1}]) == [Item(x=1)]

    await _do_async(m, {"x": 1}, Item(x=1))
