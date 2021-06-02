import asyncio
import os

import numpy as np
import pytest

from modelkit import ModelLibrary
from modelkit.core.models.tensorflow_model import TensorflowModel
from modelkit.core.settings import LibrarySettings
from modelkit.testing import tf_serving_fixture
from tests import TEST_DIR
from tests.conftest import skip_unless


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


TEST_ITEMS = [
    {"input_1": np.zeros((3, 2, 1), dtype=np.float32)},
    {"input_1": np.ones((3, 2, 1), dtype=np.float32)},
    {"input_1": 2 * np.ones((3, 2, 1), dtype=np.float32)},
    {"input_1": 3 * np.ones((3, 2, 1), dtype=np.float32)},
]


def test_tf_model_local_path():
    model = DummyTFModel(
        asset_path=os.path.join(TEST_DIR, "testdata", "dummy_tf_model", "0.0"),
        output_dtypes={"lambda": np.float32},
        output_tensor_mapping={"lambda": "nothing"},
        output_shapes={"lambda": (3, 2, 1)},
    )
    v = np.zeros((3, 2, 1), dtype=np.float32)
    assert np.allclose(v, model({"input_1": v})["lambda"])


def test_tf_model(monkeypatch, working_dir):
    monkeypatch.setenv("ASSETS_BUCKET_NAME", TEST_DIR)
    monkeypatch.setenv("STORAGE_PREFIX", "testdata")
    monkeypatch.setenv("STORAGE_PROVIDER", "local")
    monkeypatch.setenv("WORKING_DIR", working_dir)

    lib = ModelLibrary(models=DummyTFModel)
    assert not lib.settings.tf_serving.enable
    model = lib.get("dummy_tf_model")
    v = np.zeros((3, 2, 1), dtype=np.float32)
    assert np.allclose(v, model({"input_1": v})["lambda"])


@pytest.fixture(scope="function")
def tf_serving(request, monkeypatch, working_dir):
    monkeypatch.setenv("WORKING_DIR", working_dir)
    monkeypatch.setenv("ASSETS_BUCKET_NAME", TEST_DIR)
    monkeypatch.setenv("STORAGE_PREFIX", "testdata")
    monkeypatch.setenv("STORAGE_PROVIDER", "local")

    lib = ModelLibrary(models=DummyTFModel, settings={"lazy_loading": True})
    yield tf_serving_fixture(request, lib)


@skip_unless("ENABLE_TF_SERVING_TEST", "True")
def test_iso_serving_mode(tf_serving):
    model_name = "dummy_tf_model"
    # Get the prediction service running TF with gRPC serving
    svc_serving_grpc = ModelLibrary(
        required_models=[model_name],
        settings=LibrarySettings(
            tf_serving={
                "enable": True,
                "port": 8500,
                "mode": "grpc",
                "host": "localhost",
            }
        ),
        models=DummyTFModel,
    )
    model_grpc = svc_serving_grpc.get(model_name)

    svc_serving_rest = ModelLibrary(
        required_models=[model_name],
        settings=LibrarySettings(
            tf_serving={
                "enable": True,
                "port": 8501,
                "mode": "rest",
                "host": "localhost",
            }
        ),
        models=DummyTFModel,
    )
    model_rest = svc_serving_rest.get(model_name)

    # Get the prediction service running TF as a library
    svc_tflib = ModelLibrary(
        required_models=[model_name],
        settings=LibrarySettings(),
        models=DummyTFModel,
    )
    assert not svc_tflib.settings.tf_serving.enable
    model_tflib = svc_tflib.get(model_name)
    _compare_models(model_tflib, model_grpc, TEST_ITEMS)

    _compare_models(model_rest, model_grpc, TEST_ITEMS)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(svc_serving_rest.close_connections())
    loop.run_until_complete(svc_serving_grpc.close_connections())
    assert model_rest.aiohttp_session is None


def compare_result(x, y, tolerance):
    """compares the objects x and y, whether they be python immutable types,
    iterables or numerical arrays (within a given tolerance)
    """
    assert type(x) == type(y)
    if isinstance(x, dict):
        assert set(x.keys()) == set(y.keys())
        for key in x:
            assert compare_result_field(x[key], y[key], tolerance)
        return True
    if isinstance(x, tuple):
        for xx, yy in zip(x, y):
            assert compare_result_field(xx, yy, tolerance)
        return True
    return compare_result_field(x, y, tolerance)


def compare_result_field(x, y, tolerance):
    """compares the objects x and y, whether they be python immutable types,
    iterables or numerical arrays (within a given tolerance)
    """
    assert type(x) == type(y)
    if isinstance(x, np.ndarray):
        if np.issubdtype(x.dtype, np.number):
            return (_abs_difference(x, y) <= tolerance).all()
        return (x == y).all()
    if isinstance(x, (float, int, complex, bool)):
        return np.abs(x - y) <= tolerance
    return x == y


def _abs_difference(x, y):
    """a measure of the relative difference between two numbers."""
    return np.abs(x - y) / (1e-4 + (np.abs(x) + np.abs(y)) / 2)


def _compare_models(model0, model1, items, tolerance=1e-2):
    """compares two models in the following situations:
    - model0 per item vs. model1 per item
    - model0 batched vs. model1 batched
    - model0 per item vs. model0 batched
    """
    res_model0_per_item = []

    try:
        # Compare two models on single_predictions
        for item in items:
            res_model0 = model0(item)
            res_model0_per_item.append(res_model0)
            res_model1 = model1(item)
            assert compare_result(res_model0, res_model1, tolerance)
    except AssertionError as e:
        raise AssertionError(f"Models differ on single items\n{e.args[0]}")

    try:
        # Compare two models in batches
        res_model0_items = model0.predict_batch(items)
        res_model1_items = model1.predict_batch(items)
        for k in range(len(items)):
            res_model0 = res_model0_items[k]
            res_model1 = res_model1_items[k]
            assert compare_result(res_model0, res_model1, tolerance)
    except AssertionError as e:
        raise AssertionError(f"Models differ on item batches\n{e.args[0]}")

    try:
        # Compare batched vs. computed with one item
        for k in range(len(items)):
            assert compare_result(
                res_model0_items[k], res_model0_per_item[k], tolerance
            )
    except AssertionError as e:
        raise AssertionError(
            f"Models predictions on single and batches differ\n{e.args[0]}"
        )


@skip_unless("ENABLE_TF_SERVING_TEST", "True")
def test_iso_async(tf_serving):
    # Get the prediction service running TF with REST serving
    svc = ModelLibrary(
        required_models=["dummy_tf_model"],
        settings=LibrarySettings(
            tf_serving={
                "enable": True,
                "port": 8501,
                "mode": "rest",
                "host": "localhost",
            }
        ),
        models=DummyTFModel,
    )
    m_jt2s = svc.get("dummy_tf_model")

    # TODO: allow setting mode at predict time
    async_svc = ModelLibrary(
        required_models=["dummy_tf_model"],
        settings=LibrarySettings(
            tf_serving={
                "enable": True,
                "port": 8501,
                "mode": "rest-async",
                "host": "localhost",
            }
        ),
        models=DummyTFModel,
    )
    async_m_jt2s = async_svc.get("dummy_tf_model")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_compare_models_async(m_jt2s, async_m_jt2s, TEST_ITEMS))
    loop.run_until_complete(async_svc.close_connections())
    assert async_m_jt2s.aiohttp_session is None


async def _compare_models_async(model, model_async, items, tolerance=1e-2):
    """compares two models in the following situations:
    - model0 per item vs. model1 per item
    - model0 batched vs. model1 batched
    - model0 per item vs. model0 batched
    """
    res_model0_per_item = []

    try:
        # Compare two models on single_predictions
        for item in items:
            res_model0 = model(item)
            res_model0_per_item.append(res_model0)
            res_model1 = await model_async.predict_async(item)
            assert compare_result(res_model0, res_model1, tolerance)
    except AssertionError as e:
        raise AssertionError(f"Models differ on single items\n{e.args[0]}")

    try:
        # Compare two models in batches
        res_model0_items = model.predict_batch(items)
        res_model1_items = await model_async.predict_batch_async(items)
        for k in range(len(items)):
            res_model0 = res_model0_items[k]
            res_model1 = res_model1_items[k]
            assert compare_result(res_model0, res_model1, tolerance)
    except AssertionError as e:
        raise AssertionError(f"Models differ on item batches\n{e.args[0]}")

    try:
        # Compare batched vs. computed with one item
        for k in range(len(items)):
            assert compare_result(
                res_model0_items[k], res_model0_per_item[k], tolerance
            )
    except AssertionError as e:
        raise AssertionError(
            f"Models predictions on single and batches differ\n{e.args[0]}"
        )
