import pydantic

from modelkit.core.model import Model


class SomeSimpleValidatedModelB(Model[str, str]):
    """
    This is a summary

    that also has plenty more text
    """

    CONFIGURATIONS = {"some_model_b": {}}

    def _predict(self, item):
        return item


class ItemModel(pydantic.BaseModel):
    string: str


class ResultModel(pydantic.BaseModel):
    sorted: str


class SomeComplexValidatedModelB(Model[ItemModel, ResultModel]):
    """
    More complex

    With **a lot** of documentation
    """

    CONFIGURATIONS = {"some_complex_model_b": {}}

    def _predict(self, item):
        return {"sorted": "".join(sorted(item.string))}
