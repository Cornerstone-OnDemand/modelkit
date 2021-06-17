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

    def _predict(self, item, add_one=False):
        if add_one:
            return {"x": item.x + 1}
        return item


def test_list_cases():
    expected = [("some_model", {"x": 1}, {"x": 1}, {})]

    class SomeModel(Model[ModelItemType, ModelItemType]):
        CONFIGURATIONS = {"some_model": {}}

        TEST_CASES = ModelTestingConfiguration(
            cases=[{"item": {"x": 1}, "result": {"x": 1}}]
        )

        def _predict(self, item):
            return item

    assert list(SomeModel._iterate_test_cases()) == expected
    assert list(SomeModel._iterate_test_cases("some_model")) == expected
    assert list(SomeModel._iterate_test_cases("unknown_model")) == []

    class TestableModel(Model[ModelItemType, ModelItemType]):
        CONFIGURATIONS = {"some_model": {}}

        TEST_CASES = {"cases": [{"item": {"x": 1}, "result": {"x": 1}}]}

        def _predict(self, item):
            return item

    assert list(TestableModel._iterate_test_cases()) == expected
    assert list(TestableModel._iterate_test_cases("some_model")) == expected
    assert list(TestableModel._iterate_test_cases("unknown_model")) == []

    class TestableModel(Model[ModelItemType, ModelItemType]):
        CONFIGURATIONS = {
            "some_model": {
                "test_cases": {"cases": [{"item": {"x": 1}, "result": {"x": 1}}]}
            },
            "some_other_model": {},
        }
        TEST_CASES = {"cases": [{"item": {"x": 1}, "result": {"x": 1}}]}

        def _predict(self, item):
            return item

    assert list(TestableModel._iterate_test_cases()) == expected * 2 + [
        ("some_other_model", {"x": 1}, {"x": 1}, {})
    ]
    assert list(TestableModel._iterate_test_cases("some_model")) == expected * 2
    assert list(TestableModel._iterate_test_cases("unknown_model")) == []
    assert list(TestableModel._iterate_test_cases("some_other_model")) == [
        ("some_other_model", {"x": 1}, {"x": 1}, {})
    ]


# This function creates the test_auto_model_library test
# but also a fixture called testing_model_library with a
# ModelLibrary
# pytest will run the test_auto_model_library test
modellibrary_fixture(
    models=TestableModel,
    fixture_name="testing_model_library",
)

modellibrary_auto_test(
    models=TestableModel,
    fixture_name="testing_model_library",
    test_name="test_auto_model_library",
)


# The fixture with the ModelLibrary can be used elsewhere as usual
def test_testing_model_library(testing_model_library):
    m = testing_model_library.get("some_model")
    assert m({"x": 1}).x == 1
