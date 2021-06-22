from typing import Dict

import pydantic
import pytest

from modelkit.core.model import Model
from modelkit.testing import modellibrary_auto_test, modellibrary_fixture


class ModelItemType(pydantic.BaseModel):
    x: int


class ModelReturnType(pydantic.BaseModel):
    x: int


class TestableModel(Model[ModelItemType, ModelItemType]):
    CONFIGURATIONS: Dict[str, Dict] = {"some_model": {}}

    TEST_CASES = [
        {"item": {"x": 1}, "result": {"x": 1}},
        {"item": {"x": 2}, "result": {"x": 2}},
        {"item": {"x": 1}, "result": {"x": 2}, "keyword_args": {"add_one": True}},
    ]

    def _predict(self, item, add_one=False):
        if add_one:
            return {"x": item.x + 1}
        return item


def test_list_cases():
    expected = [("some_model", {"x": 1}, {"x": 1}, {})]

    class SomeModel(Model[ModelItemType, ModelItemType]):
        CONFIGURATIONS = {"some_model": {}}

        TEST_CASES = [{"item": {"x": 1}, "result": {"x": 1}}]

        def _predict(self, item):
            return item

    assert list(SomeModel._iterate_test_cases()) == expected
    assert list(SomeModel._iterate_test_cases("some_model")) == expected
    assert list(SomeModel._iterate_test_cases("unknown_model")) == []

    class TestableModel(Model[ModelItemType, ModelItemType]):
        CONFIGURATIONS = {"some_model": {}}

        TEST_CASES = [{"item": {"x": 1}, "result": {"x": 1}}]

        def _predict(self, item):
            return item

    assert list(TestableModel._iterate_test_cases()) == expected
    assert list(TestableModel._iterate_test_cases("some_model")) == expected
    assert list(TestableModel._iterate_test_cases("unknown_model")) == []

    class TestableModel(Model[ModelItemType, ModelItemType]):
        CONFIGURATIONS = {
            "some_model": {"test_cases": [{"item": {"x": 1}, "result": {"x": 1}}]},
            "some_other_model": {},
        }
        TEST_CASES = [{"item": {"x": 1}, "result": {"x": 1}}]

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


@pytest.mark.parametrize(
    "test_case, do_raise",
    [
        ({"item": True, "result": True}, False),
        ({"item": False, "result": True}, True),
        ({"item": False, "keyword_args": {"force_true": True}, "result": True}, False),
        ({"item": False, "keyword_args": {"force_true": False}, "result": True}, True),
    ],
)
def test_auto_test_function(test_case, do_raise):
    class MyModel(Model):
        CONFIGURATIONS = {"my_model": {}}
        TEST_CASES = [test_case]

        def _predict(self, item: bool, force_true=False, **_) -> bool:
            if force_true:
                return True
            return item

    if do_raise:
        with pytest.raises(AssertionError):
            MyModel().test()
    else:
        MyModel().test()
