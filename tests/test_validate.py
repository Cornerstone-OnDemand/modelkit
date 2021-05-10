from typing import Any, Dict

import pydantic
import pytest

from modelkit.core.model import (
    ItemValidationException,
    Model,
    ReturnValueValidationException,
)


def test_validate_item_spec_pydantic():
    class ItemModel(pydantic.BaseModel):
        x: int

    class SomeValidatedModel(Model[ItemModel, Any]):
        async def _predict_one(self, item):
            return item

    valid_test_item = {"x": 10}

    m = SomeValidatedModel()
    assert m.predict(valid_test_item) == valid_test_item

    with pytest.raises(ItemValidationException):
        m.predict({"ok": 1})

    with pytest.raises(ItemValidationException):
        m.predict({"x": "something", "blabli": 10})

    assert m.predict([valid_test_item] * 2) == [valid_test_item] * 2


def test_validate_item_spec_pydantic_default():
    class ItemType(pydantic.BaseModel):
        x: int
        y: str = "ok"

    class ReturnType(pydantic.BaseModel):
        result: int
        something_else: str = "ok"

    class TypedModel(Model[ItemType, ReturnType]):
        async def _predict_one(self, item, **kwargs):
            return {"result": item.x + len(item.y)}

    m = TypedModel()
    res = m.predict({"x": 10, "y": "okokokokok"})
    assert res.result == 20
    assert res.something_else == "ok"
    res = m.predict({"x": 10})
    assert res.result == 12
    assert res.something_else == "ok"

    with pytest.raises(ItemValidationException):
        m.predict({})


def test_validate_item_spec_typing():
    class SomeValidatedModel(Model[Dict[str, int], Any]):
        async def _predict_one(self, item):
            return item

    valid_test_item = {"x": 10}

    m = SomeValidatedModel()
    assert m.predict(valid_test_item) == valid_test_item

    with pytest.raises(ItemValidationException):
        m.predict(["ok"])

    with pytest.raises(ItemValidationException):
        m.predict("x")

    with pytest.raises(ItemValidationException):
        m.predict([1, 2, 1])

    assert m.predict([valid_test_item] * 2) == [valid_test_item] * 2


def test_validate_return_spec():
    class ItemModel(pydantic.BaseModel):
        x: int

    class SomeValidatedModel(Model[Any, ItemModel]):
        async def _predict_one(self, item):
            return item

    m = SomeValidatedModel()
    ret = m.predict({"x": 10})
    assert ret.x == 10

    with pytest.raises(ReturnValueValidationException):
        m.predict({"x": "something", "blabli": 10})


def test_validate_list_items():
    class ItemModel(pydantic.BaseModel):
        x: str
        y: str = "ok"

    class SomeValidatedModel(Model[ItemModel, Any]):
        def __init__(self, *args, **kwargs):
            self.counter = 0
            super().__init__(*args, **kwargs)

        async def _predict_one(self, item):
            self.counter += 1
            return item

    m = SomeValidatedModel()
    m.predict([{"x": 10, "y": "ko"}] * 10)
    assert m.counter == 10
    m.predict({"x": 10, "y": "ko"})
    assert m.counter == 11


def test_validate_none():
    class SomeValidatedModel(Model):
        async def _predict_one(self, item):
            return item

    m = SomeValidatedModel()
    assert m.predict({"x": 10}) == {"x": 10}
    assert m.predict(1) == 1
