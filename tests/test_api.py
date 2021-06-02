import os
import platform

import fastapi
import numpy as np
import pydantic
import pytest
from starlette.testclient import TestClient

from modelkit import testing
from modelkit.api import ModelkitAutoAPIRouter
from modelkit.core.model import Asset, Model
from tests import TEST_DIR


@pytest.fixture(scope="module")
def api_no_type(event_loop):
    class SomeSimpleValidatedModel(Model[str, str]):
        """
        This is a summary

        that also has plenty more text
        """

        CONFIGURATIONS = {"some_model": {}}

        def _predict(self, item):
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

        def _predict(self, item):
            return {"sorted": "".join(sorted(item.string))}

    class NotValidatedModel(Model):
        CONFIGURATIONS = {"unvalidated_model": {}}

        def _predict(self, item):
            return item

    class ValidationNotSupported(Model[np.ndarray, np.ndarray]):
        CONFIGURATIONS = {"no_supported_model": {}}

        def _predict(self, item):
            return item

    class SomeAsset(Asset):
        """
        This is not a Model, it won't appear in the service
        """

        CONFIGURATIONS = {"some_asset": {}}

        def _predict(self, item):
            return {"sorted": "".join(sorted(item.string))}

    router = ModelkitAutoAPIRouter(
        required_models=[
            "unvalidated_model",
            "no_supported_model",
            "some_model",
            "some_complex_model",
            "some_asset",
        ],
        models=[
            ValidationNotSupported,
            NotValidatedModel,
            SomeSimpleValidatedModel,
            SomeComplexValidatedModel,
            SomeAsset,
        ],
    )

    app = fastapi.FastAPI()
    app.include_router(router)

    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize("item", ["ok", "ko"])
def test_api_simple_type(item, api_no_type):
    res = api_no_type.post(
        "/predict/some_model", headers={"Content-Type": "application/json"}, json=item
    )
    assert res.status_code == 200
    assert res.json() == item

    res = api_no_type.post(
        "/predict/batch/some_model",
        headers={"Content-Type": "application/json"},
        json=[item],
    )
    assert res.status_code == 200
    assert res.json() == [item]


@pytest.mark.parametrize("item", [{"string": "ok"}])
def test_api_complex_type(item, api_no_type):
    res = api_no_type.post(
        "/predict/some_complex_model",
        headers={"Content-Type": "application/json"},
        json=item,
    )
    assert res.status_code == 200
    assert res.json()["sorted"] == "".join(sorted(item["string"]))

    res = api_no_type.post(
        "/predict/batch/some_complex_model",
        headers={"Content-Type": "application/json"},
        json=[item],
    )
    assert res.status_code == 200
    assert res.json()[0]["sorted"] == "".join(sorted(item["string"]))


EXCLUDED = ["load time", "load memory"]


def _strip_description_fields(spec):
    if isinstance(spec, str):
        return "\n".join(
            line for line in spec.split("\n") if not any(x in line for x in EXCLUDED)
        )
    if isinstance(spec, list):
        return [_strip_description_fields(x) for x in spec]
    if isinstance(spec, dict):
        return {key: _strip_description_fields(value) for key, value in spec.items()}
    return spec


def test_api_doc(api_no_type):
    r = testing.ReferenceJson(os.path.join(TEST_DIR, "testdata", "api"))
    res = api_no_type.get(
        "/openapi.json",
    )
    if platform.system() != "Windows":
        # Output is different on Windows platforms since
        # modelkit.utils.memory cannot track memory increment
        # and write it
        r.assert_equal("openapi.json", _strip_description_fields(res.json()))
