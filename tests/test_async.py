import asyncio

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
