from typing import Any, Dict

from modelkit.core.library import ModelLibrary
from modelkit.core.model import Model


class SomeModelNoOtherFun(Model):
    CONFIGURATIONS: Dict[str, Any] = {"something2": {}}


lib = ModelLibrary(models=SomeModelNoOtherFun)

m_get = lib.get("something2", model_type=SomeModelNoOtherFun)
m_get.do_something_model_does_not()
