from typing import Dict

import pydantic

from modelkit.core.model import Model
from modelkit.core.types import ModelTestingConfiguration
from modelkit.testing import modellibrary_auto_test, modellibrary_fixture


class ModelItemType(pydantic.BaseModel):
    x: int


class ModelReturnType(pydantic.BaseModel):
    x: int


class TestableModel(Model[ModelItemType, ModelItemType]):
    CONFIGURATIONS: Dict[str, Dict] = {"some_model": {}}

    TEST_CASES = {
        "cases": [
            {"item": {"x": 1}, "result": {"x": 1}},
            {"item": {"x": 2}, "result": {"x": 2}},
            {"item": {"x": 1}, "result": {"x": 2}, "keyword_args": {"add_one": True}},
        ]
    }

    async def _predict_one(self, item, add_one=False):
        if add_one:
            return {"x": item.x + 1}
        return item


def test_list_cases():
    class SomeModel(Model[ModelItemType, ModelItemType]):
        CONFIGURATIONS = {"some_model": {}}

        TEST_CASES = ModelTestingConfiguration(
            cases=[{"item": {"x": 1}, "result": {"x": 1}}]
        )

        async def _predict_one(self, item):
            return item

    assert list(SomeModel._iterate_test_cases()) == [
        ("some_model", {"x": 1}, {"x": 1}, {})
    ]

    class TestableModel(Model[ModelItemType, ModelItemType]):
        CONFIGURATIONS = {"some_model": {}}

        TEST_CASES = {"cases": [{"item": {"x": 1}, "result": {"x": 1}}]}

        async def _predict_one(self, item):
            return item

    assert list(TestableModel._iterate_test_cases()) == [
        ("some_model", {"x": 1}, {"x": 1}, {})
    ]


# This function creates the test_auto_prediction_service test
# but also a fixture called testing_prediction_service with a
# ModelLibrary
# pytest will run the test_auto_prediction_service test
modellibrary_fixture(
    models=TestableModel,
    fixture_name="testing_prediction_service",
)

modellibrary_auto_test(
    models=TestableModel,
    fixture_name="testing_prediction_service",
    test_name="test_auto_prediction_service",
)


# The fixture with the ModelLibrary can be used elsewhere as usual
def test_testing_prediction_service(testing_prediction_service):
    m = testing_prediction_service.get_model("some_model")
    assert m.predict({"x": 1}).x == 1
