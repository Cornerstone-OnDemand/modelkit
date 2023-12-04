from typing import Any, Dict, List

import pydantic
import pytest

from modelkit.core.errors import (
    ItemValidationException,
    ModelkitDataValidationException,
    ReturnValueValidationException,
)
from modelkit.core.model import AsyncModel, Model
from modelkit.core.settings import LibrarySettings


def test_validate_item_spec_pydantic():
    service_settings = LibrarySettings()

    class ItemModel(pydantic.BaseModel):
        x: int

    class SomeValidatedModel(Model[ItemModel, Any]):
        def _predict(self, item):
            return item

    valid_test_item = {"x": 10}

    m = SomeValidatedModel(service_settings=service_settings)
    assert m(valid_test_item).model_dump() == valid_test_item

    with pytest.raises(ItemValidationException):
        m({"ok": 1})
    with pytest.raises(ItemValidationException):
        m({"x": "something", "blabli": 10})

    assert [x.model_dump() for x in m.predict_batch([valid_test_item] * 2)] == [
        valid_test_item
    ] * 2


@pytest.mark.asyncio
async def test_validate_item_spec_pydantic_async():
    service_settings = LibrarySettings()

    class ItemModel(pydantic.BaseModel):
        x: int

    class AsyncSomeValidatedModel(AsyncModel[ItemModel, Any]):
        async def _predict(self, item):
            return item

    valid_test_item = ItemModel(x=10)

    m = AsyncSomeValidatedModel(service_settings=service_settings)
    res = await m(valid_test_item)
    assert res == valid_test_item

    with pytest.raises(ItemValidationException):
        await m({"ok": 1})
    with pytest.raises(ItemValidationException):
        await m({"x": "something", "blabli": 10})

    res_list = await m.predict_batch([valid_test_item] * 2)
    assert res_list == [valid_test_item] * 2


def test_validate_item_spec_pydantic_default():
    service_settings = LibrarySettings()

    class ItemType(pydantic.BaseModel):
        x: int
        y: str = "ok"

    class ReturnType(pydantic.BaseModel):
        result: int
        something_else: str = "ok"

    class TypedModel(Model[ItemType, ReturnType]):
        def _predict(self, item, **kwargs):
            return {"result": item.x + len(item.y)}

    m = TypedModel(service_settings=service_settings)
    res = m({"x": 10, "y": "okokokokok"})
    assert res.result == 20
    assert res.something_else == "ok"
    res = m({"x": 10})
    assert res.result == 12
    assert res.something_else == "ok"

    with pytest.raises(ItemValidationException):
        m({})


def test_validate_item_spec_typing():
    service_settings = LibrarySettings()

    class SomeValidatedModel(Model[Dict[str, int], Any]):
        def _predict(self, item):
            return item

    valid_test_item = {"x": 10}

    m = SomeValidatedModel(service_settings=service_settings)
    assert m(valid_test_item) == valid_test_item

    with pytest.raises(ItemValidationException):
        m.predict_batch(["ok"])

    with pytest.raises(ItemValidationException):
        m("x")

    with pytest.raises(ItemValidationException):
        m.predict_batch([1, 2, 1])

    assert m.predict_batch([valid_test_item] * 2) == [valid_test_item] * 2


def test_validate_return_spec():
    service_settings = LibrarySettings()

    class ItemModel(pydantic.BaseModel):
        x: int

    class SomeValidatedModel(Model[Any, ItemModel]):
        def _predict(self, item):
            return item

    m = SomeValidatedModel(service_settings=service_settings)
    ret = m({"x": 10})
    assert ret.x == 10

    with pytest.raises(ReturnValueValidationException):
        m({"x": "something", "blabli": 10})


def test_validate_list_items():
    service_settings = LibrarySettings()

    class ItemModel(pydantic.BaseModel):
        x: str
        y: str = "ok"

    class SomeValidatedModel(Model[ItemModel, Any]):
        def __init__(self, *args, **kwargs):
            self.counter = 0
            super().__init__(*args, **kwargs)

        def _predict(self, item):
            self.counter += 1
            return item

    m = SomeValidatedModel(service_settings=service_settings)
    m.predict_batch([{"x": "10", "y": "ko"}] * 10)
    assert m.counter == 10
    m({"x": "10", "y": "ko"})
    assert m.counter == 11


def test_validate_none():
    service_settings = LibrarySettings()

    class SomeValidatedModel(Model):
        def _predict(self, item):
            return item

    m = SomeValidatedModel(service_settings=service_settings)
    assert m({"x": 10}) == {"x": 10}
    assert m(1) == 1


def test_pydantic_error_truncation():
    class ListModel(pydantic.BaseModel):
        values: List[int]

    # This will trigger the error truncation
    with pytest.raises(ModelkitDataValidationException):
        try:
            ListModel(values=["ok"] * 100)
        except pydantic.ValidationError as exc:
            raise ModelkitDataValidationException(
                "test error", pydantic_exc=exc
            ) from exc

    # This will not
    with pytest.raises(ModelkitDataValidationException):
        try:
            ListModel(values=["ok"])
        except pydantic.ValidationError as exc:
            raise ModelkitDataValidationException(
                "test error", pydantic_exc=exc
            ) from exc
