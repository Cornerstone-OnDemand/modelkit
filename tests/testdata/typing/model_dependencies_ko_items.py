from typing import Any, Dict

from modelkit.core.library import ModelLibrary
from modelkit.core.model import Model


class SomeModel(Model[str, str]):
    CONFIGURATIONS: Dict[str, Any] = {"dependent": {}}

    def _predict(self, item):
        return item


class SomeOtherModel(Model[int, int]):
    CONFIGURATIONS: Dict[str, Any] = {
        "something": {"model_dependencies": {"dependent"}}
    }

    def _predict(self, item):
        m = self.model_dependencies.get("dependent", SomeModel)
        res = m.predict(item)
        return res


lib = ModelLibrary(models=[SomeModel, SomeOtherModel])

m2 = lib.get("something", model_type=SomeOtherModel)
m2.predict("str")
