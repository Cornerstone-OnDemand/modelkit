import pydantic

from modelkit.core.model import Model


class ItemModel(pydantic.BaseModel):
    x: int


class SomeBadValidatedModel(Model[ItemModel, ItemModel]):
    async def _predict_one(self, item):
        return item.x


m = SomeBadValidatedModel()
y: int = m.predict(ItemModel(x=10))  # here mypy expects an ItemModel to be returned
