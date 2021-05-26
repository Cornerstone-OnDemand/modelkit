import pydantic

from modelkit.core.model import Model


class ItemModel(pydantic.BaseModel):
    x: int


class SomeValidatedModel(Model[ItemModel, ItemModel]):
    async def _predict_one(self, item):
        return item


m = SomeValidatedModel()
y: ItemModel = m(ItemModel(x=10))
