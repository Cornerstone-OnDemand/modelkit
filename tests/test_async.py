import asyncio

import pydantic
import pytest
from asgiref.sync import AsyncToSync

from modelkit.core.library import ModelLibrary
from modelkit.core.model import AsyncModel, Model, WrappedAsyncModel


def test_compose_sync_async():
    class SomeAsyncModel(AsyncModel):
        CONFIGURATIONS = {"async_model": {}}

        async def _predict(self, item, **kwargs):
            await asyncio.sleep(0)
            return item

    class ComposedModel(Model):
        CONFIGURATIONS = {"composed_model": {"model_dependencies": {"async_model"}}}

        def _predict(self, item, **kwargs):
            self.model_dependencies["async_model"].predict_batch([item])
            return self.model_dependencies["async_model"].predict(item)

    library = ModelLibrary(models=[SomeAsyncModel, ComposedModel])
    m = library.get("composed_model")
    assert isinstance(m.model_dependencies["async_model"], WrappedAsyncModel)
    assert m.predict({"hello": "world"}) == {"hello": "world"}


def test_compose_sync_async_generator_fail():
    class SomeAsyncModel(AsyncModel):
        CONFIGURATIONS = {"async_model": {}}

        async def _predict(self, item, **kwargs):
            await asyncio.sleep(0)
            return item

        async def close(self):
            await asyncio.sleep(0)

    class ComposedModel(Model):
        CONFIGURATIONS = {"composed_model": {"model_dependencies": {"async_model"}}}

        def _predict(self, item, **kwargs):
            # The following does not currently work, because AsyncToSync does not
            # seem to correctly wrap asynchronous generators
            for r in AsyncToSync(  # noqa: B007
                self.model_dependencies["async_model"].async_model.predict_gen
            )(iter((item,))):
                break
            return r

    library = ModelLibrary(models=[SomeAsyncModel, ComposedModel])
    m = library.get("composed_model")
    assert isinstance(m.model_dependencies["async_model"], WrappedAsyncModel)
    with pytest.raises(TypeError):
        # raises
        # TypeError: object async_generator can't be used in 'await' expression
        assert m.predict({"hello": "world"}) == {"hello": "world"}

    library.close()


@pytest.mark.asyncio
async def test_compose_async_sync_async(event_loop):
    class SomeAsyncModel(AsyncModel):
        CONFIGURATIONS = {"async_model": {}}

        async def _predict(self, item):
            await asyncio.sleep(0)
            return item

    class ComposedModel(Model):
        CONFIGURATIONS = {"composed_model": {"model_dependencies": {"async_model"}}}

        def _predict(self, item):
            return self.model_dependencies["async_model"].predict(item)

    class SomeAsyncComposedModel(AsyncModel):
        CONFIGURATIONS = {
            "async_composed_model": {"model_dependencies": {"composed_model"}}
        }

        async def _predict(self, item):
            await asyncio.sleep(0)
            return await self.model_dependencies["composed_model"].predict(item)

    library = ModelLibrary(
        models=[SomeAsyncComposedModel, SomeAsyncModel, ComposedModel]
    )
    m = library.get("async_composed_model")
    res = await m.predict({"hello": "world"})
    assert res == {"hello": "world"}
    async for res in m.predict_gen(iter(({"hello": "world"},))):
        assert res == {"hello": "world"}
    res = await m.predict_batch([{"hello": "world"}])
    assert res == [{"hello": "world"}]
    await library.aclose()


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
            await asyncio.sleep(0)
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
            await asyncio.sleep(0)
            return item

    m = SomeModel()
    with pytest.raises(AssertionError):
        assert m.predict({"x": 1}) == Item(x=1)
    with pytest.raises(AssertionError):
        assert m.predict_batch([{"x": 1}]) == [Item(x=1)]

    await _do_async(m, {"x": 1}, Item(x=1))
