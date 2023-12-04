import pickle  # nosec

import pydantic

from modelkit.core.model import Model


class ItemType(pydantic.BaseModel):
    x: int


class ReturnType(pydantic.BaseModel):
    x: int


class SomeModel(Model[ItemType, ReturnType]):
    def _predict(self, item):
        return {"x": item.x}


def test_model_serialization():
    m = SomeModel()
    # To be used on Spark, models need to be pickled, so we have a test for that. It's
    # not an insecure use of pickle, which is why we use the `nosec` comment.
    re_m = pickle.loads(pickle.dumps(m))  # nosec
    assert re_m({"x": 1}).x == 1


class SomeModelWithoutTypes(Model):
    def _predict(self, item):
        return item


def test_model_serialization_without_types():
    m = SomeModelWithoutTypes()
    # To be used on Spark, models need to be pickled, so we have a test for that. It's
    # not an insecure use of pickle, which is why we use the `nosec` comment.
    re_m = pickle.loads(pickle.dumps(m))  # nosec
    assert re_m({"x": 1}) == {"x": 1}
