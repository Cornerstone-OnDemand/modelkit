from typing import Any, Dict

from modelkit.core.library import ModelLibrary
from modelkit.core.model import Model


class SomeModel(Model):
    CONFIGURATIONS: Dict[str, Any] = {"something": {}}

    def do_something_model_does_not(self):
        return True


lib = ModelLibrary(models=SomeModel)

m2 = lib.get("something", model_type=SomeModel)
m2.do_something_model_does_not()
