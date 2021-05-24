import os

import fastapi
import pydantic
import pytest
from starlette.testclient import TestClient

from modelkit import testing
from modelkit.api import ModelkitAutoAPIRouter
from modelkit.core.model import Model
from tests import TEST_DIR


@pytest.fixture(scope="session")
def api_no_type(event_loop):
    class SomeSimpleValidatedModel(Model[str, str]):
        """
        This is a summary

        that also has plenty more text
        """

        CONFIGURATIONS = {"some_model": {}}

        async def _predict_one(self, item):
            return item

    class ItemModel(pydantic.BaseModel):
        string: str

    class ResultModel(pydantic.BaseModel):
        sorted: str

    class SomeComplexValidatedModel(Model[ItemModel, ResultModel]):
        """
        More complex

        With **a lot** of documentation
        """

        CONFIGURATIONS = {"some_complex_model": {}}

        async def _predict_one(self, item):
            return {"sorted": "".join(sorted(item.string))}

    router = ModelkitAutoAPIRouter(
        required_models=["some_model", "some_complex_model"],
        models=[SomeSimpleValidatedModel, SomeComplexValidatedModel],
    )

    app = fastapi.FastAPI()
    app.include_router(router)

    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize("item", ["ok", ["ok", "ko"]])
def test_api_simple_type(item, api_no_type):
    res = api_no_type.post(
        "/predict/some_model", headers={"Content-Type": "application/json"}, json=item
    )
    assert res.status_code == 200
    assert res.json() == item


@pytest.mark.parametrize("item", [{"string": "ok"}])
def test_api_complex_type(item, api_no_type):
    res = api_no_type.post(
        "/predict/some_complex_model",
        headers={"Content-Type": "application/json"},
        json=item,
    )
    assert res.status_code == 200
    assert res.json()["sorted"] == "".join(sorted(item["string"]))


def test_api_doc(api_no_type):
    r = testing.ReferenceJson(os.path.join(TEST_DIR, "testdata", "api"))
    res = api_no_type.get(
        "/openapi.json",
    )
    r.assert_equal("openapi.json", res.json())
