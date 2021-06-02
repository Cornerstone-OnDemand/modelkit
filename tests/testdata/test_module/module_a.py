import numpy as np
import pydantic

from modelkit.core.model import Model
from modelkit.core.models.tensorflow_model import TensorflowModel


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


class SomeComplexValidatedModelA(Model[ItemModel, ResultModel]):
    """
    More complex

    With **a lot** of documentation
    """

    CONFIGURATIONS = {"some_complex_model_a": {}}

    async def _predict(self, item):
        return {"sorted": "".join(sorted(item.string))}


class DummyTFModel(TensorflowModel):
    CONFIGURATIONS = {
        "dummy_tf_model": {
            "asset": "dummy_tf_model:0.0",
            "model_settings": {
                "output_dtypes": {"lambda": np.float32},
                "output_tensor_mapping": {"lambda": "nothing"},
                "output_shapes": {"lambda": (3, 2, 1)},
            },
        }
    }
