import os
import platform

import pydantic
from rich.console import Console

from modelkit.core.library import ModelLibrary
from modelkit.core.model import Model
from modelkit.testing import ReferenceText
from tests import TEST_DIR


def test_describe():
    class SomeSimpleValidatedModelA(Model[str, str]):
        """
        This is a summary

        that also has plenty more text
        """

        CONFIGURATIONS = {"some_model_a": {}}

        async def _predict(self, item):
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

        async def _predict(self, item):
            return item

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
