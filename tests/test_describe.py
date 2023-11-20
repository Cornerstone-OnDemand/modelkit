import os
import platform
from typing import Any

import pydantic
import pytest
from rich.console import Console

from modelkit.core.library import ModelLibrary
from modelkit.core.model import Model, add_dependencies_load_info
from modelkit.testing import ReferenceText
from modelkit.utils.pretty import describe
from tests import TEST_DIR


def test_describe(monkeypatch):
    monkeypatch.setenv(
        "MODELKIT_ASSETS_DIR", os.path.join(TEST_DIR, "testdata", "test-bucket")
    )

    class SomeSimpleValidatedModelWithAsset(Model[str, str]):
        """
        This is a summary

        that also has plenty more text
        """

        CONFIGURATIONS = {"some_model_a": {"asset": "assets-prefix"}}

        def _predict(self, item):
            return item

    class SomeSimpleValidatedModelA(Model[str, str]):
        """
        This is a summary

        that also has plenty more text
        """

        CONFIGURATIONS = {"some_model_a": {}}

        def _predict(self, item):
            return item

    class ItemModel(pydantic.BaseModel):
        string: str

    class ResultModel(pydantic.BaseModel):
        sorted: str

    class A:
        def __init__(self):
            self.x = 1
            self.y = 2

    class SomeComplexValidatedModelA(Model[ItemModel, ResultModel]):
        """
        More complex

        With **a lot** of documentation
        """

        CONFIGURATIONS = {
            "some_complex_model_a": {
                "model_dependencies": ["some_model_a"],
                "asset": os.path.join(
                    TEST_DIR,
                    "testdata",
                    "test-bucket",
                    "assets-prefix",
                    "category",
                    "asset",
                    "0.0",
                ),
                "model_settings": {"batch_size": 128},
            }
        }

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.some_object = A()

        def _predict(self, item):
            return item

    # test without a console and no models
    library = ModelLibrary()
    library.describe()

    # test with assets
    library = ModelLibrary(
        models=[
            SomeSimpleValidatedModelA,
            SomeSimpleValidatedModelWithAsset,
            SomeComplexValidatedModelA,
        ]
    )
    library.describe()

    # test with models but not assets
    library = ModelLibrary(
        models=[SomeSimpleValidatedModelA, SomeComplexValidatedModelA]
    )
    console = Console(no_color=True, force_terminal=False, width=130)

    with console.capture() as capture:
        library.describe(console=console)

    if platform.system() == "Windows" or platform.python_version().split(".")[:2] != [
        "3",
        "11",
    ]:
        # Output is different on Windows platforms since
        # modelkit.utils.memory cannot track memory increment
        # and write it
        # It also has a few minor typing differences depending on
        # the python version
        return
    r = ReferenceText(os.path.join(TEST_DIR, "testdata"))
    captured = capture.get()
    EXCLUDED = ["load time", "load memory", "asset", "category/asset", os.path.sep]
    captured = "\n".join(
        line for line in captured.split("\n") if not any(x in line for x in EXCLUDED)
    )
    r.assert_equal("library_describe.txt", captured)


class SomeObject:
    def __init__(self) -> None:
        self._x = 1
        self.y = 2


class SomePydanticModel(pydantic.BaseModel):
    ...


@pytest.mark.parametrize(
    "value",
    [
        "something",
        1,
        2,
        None,
        {"x": 1},
        [1, 2, 3],
        [1, 2, 3, [4]],
        object(),
        SomePydanticModel(),
        int,
        SomeObject(),
        float,
        Any,
        lambda x: 1,
        b"ok",
        (x for x in range(10)),
    ],
)
def test_pretty_describe(value):
    describe(value)


def test_describe_load_info():
    class top(Model[str, str]):
        CONFIGURATIONS = {
            "top": {
                "model_dependencies": ["right", "left"],
            }
        }

        def _predict(self, item):
            return item

    class right(Model[str, str]):
        CONFIGURATIONS = {
            "right": {
                "model_dependencies": ["right_dep", "join_dep"],
            }
        }

        def _predict(self, item):
            return item

    class left(Model[str, str]):
        CONFIGURATIONS = {
            "left": {
                "model_dependencies": ["join_dep"],
            }
        }

        def _predict(self, item):
            return item

    class right_dep(Model[str, str]):
        CONFIGURATIONS = {"right_dep": {}}

        def _predict(self, item):
            return item

    class join_dep(Model[str, str]):
        CONFIGURATIONS = {"join_dep": {}}

        def _predict(self, item):
            return item

    console = Console(no_color=True, force_terminal=False, width=130)

    library = ModelLibrary(models=[top, right, left, join_dep, right_dep])
    for m in ["top", "right", "left", "join_dep", "right_dep"]:
        library.get(m)._load_time = 0.1
        library.get(m)._load_memory_increment = 2

    load_info_top = {}
    add_dependencies_load_info(load_info_top, library.get("top"))
    assert load_info_top == {
        "right": {"time": 0.1, "memory_increment": 2},
        "left": {"time": 0.1, "memory_increment": 2},
        "join_dep": {"time": 0.1, "memory_increment": 2},
        "right_dep": {"time": 0.1, "memory_increment": 2},
    }

    load_info_right = {}
    add_dependencies_load_info(load_info_right, library.get("right"))
    assert load_info_right == {
        "join_dep": {"time": 0.1, "memory_increment": 2},
        "right_dep": {"time": 0.1, "memory_increment": 2},
    }

    load_info_join_dep = {}
    add_dependencies_load_info(load_info_join_dep, library.get("join_dep"))
    assert load_info_join_dep == {}

    if platform.system() == "Windows" or platform.python_version().split(".")[:2] != [
        "3",
        "11",
    ]:
        # Output is different on Windows platforms since
        # modelkit.utils.memory cannot track memory increment
        # and write it
        # It also has a few minor typing differences depending on
        # the python version
        return
    with console.capture() as capture:
        console.print("join_dep describe:")
        console.print(library.get("join_dep").describe())
        console.print()
        console.print("top describe:")
        console.print(library.get("top").describe())
    r = ReferenceText(os.path.join(TEST_DIR, "testdata"))
    r.assert_equal("test_describe_load_info.txt", capture.get())
