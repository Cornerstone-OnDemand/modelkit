import os
import platform
from typing import Any

import pydantic
import pytest
from rich.console import Console

from modelkit.core.library import ModelLibrary
from modelkit.core.model import Model
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

        CONFIGURATIONS = {"some_complex_model_a": {}}

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
    console = Console()

    with console.capture() as capture:
        library.describe(console=console)

    if platform.system() != "Windows":
        # Output is different on Windows platforms since
        # modelkit.utils.memory cannot track memory increment
        # and write it
        r = ReferenceText(os.path.join(TEST_DIR, "testdata"))
        captured = capture.get()
        EXCLUDED = ["load time", "load memory"]
        captured = "\n".join(
            line
            for line in captured.split("\n")
            if not any(x in line for x in EXCLUDED)
        )
        r.assert_equal("library_describe.txt", captured)


class SomeObject:
    def __init__(self) -> None:
        self._x = 1
        self.y = 2


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
        pydantic.BaseModel(),
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
