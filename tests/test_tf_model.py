import os

import pytest
import requests

from modelkit import ModelLibrary, testing
from modelkit.core.settings import LibrarySettings
from tests import TEST_DIR
from tests.conftest import skip_unless

try:
    from modelkit.core.models.tensorflow_model import (
        AsyncTensorflowModel,
        TensorflowModel,
    )
    from modelkit.testing import tf_serving_fixture
    from modelkit.utils.tensorflow import write_config
except NameError:
    # This occurs because type annotations in
    # modelkit.core.models.tensorflow_model will raise
    # `NameError: name 'prediction_service_pb2_grpc' is not defined`
    # when tensorflow-serving-api is not installed
    pass

np = pytest.importorskip("numpy")
grpc = pytest.importorskip("grpc")


@pytest.fixture
def dummy_tf_models():
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

        def _is_empty(self, item):
            if item["input_1"][0, 0, 0] == -1:
                return True
            return False

    class DummyTFModelNoIsEmpty(TensorflowModel):
        CONFIGURATIONS = {
            "dummy_tf_model_no_is_empty": {
                "asset": "dummy_tf_model:0.0",
                "model_settings": {
                    "output_dtypes": {"lambda": np.float32},
                    "output_tensor_mapping": {"lambda": "nothing"},
                    "output_shapes": {"lambda": (3, 2, 1)},
                    "tf_model_name": "dummy_tf_model",
                },
            }
        }

    class DummyTFModelAsync(AsyncTensorflowModel):
        CONFIGURATIONS = {
            "dummy_tf_model_async": {
                "asset": "dummy_tf_model:0.0",
                "model_settings": {
                    "output_dtypes": {"lambda": np.float32},
                    "output_tensor_mapping": {"lambda": "nothing"},
                    "output_shapes": {"lambda": (3, 2, 1)},
                    "tf_model_name": "dummy_tf_model",
                },
            }
        }

        def _is_empty(self, item):
            if item["input_1"][0, 0, 0] == -1:
                return True
            return False

    return DummyTFModel, DummyTFModelAsync, DummyTFModelNoIsEmpty


TEST_ITEMS = [
    (
        {"input_1": np.zeros((3, 2, 1), dtype=np.float32)},
        {"lambda": np.zeros((3, 2, 1), dtype=np.float32)},
    ),
    (
        {"input_1": np.ones((3, 2, 1), dtype=np.float32)},
        {"lambda": np.ones((3, 2, 1), dtype=np.float32)},
    ),
    (
        {"input_1": 2 * np.ones((3, 2, 1), dtype=np.float32)},
        {"lambda": 2 * np.ones((3, 2, 1), dtype=np.float32)},
    ),
    (
        {"input_1": 3 * np.ones((3, 2, 1), dtype=np.float32)},
        {"lambda": 3 * np.ones((3, 2, 1), dtype=np.float32)},
    ),
    (
        {"input_1": -1 * np.ones((3, 2, 1), dtype=np.float32)},
        {"lambda": -1 * np.ones((3, 2, 1), dtype=np.float32)},
    ),
]

TEST_ITEMS_IS_EMPTY = [
    (
        {"input_1": np.zeros((3, 2, 1), dtype=np.float32)},
        {"lambda": np.zeros((3, 2, 1), dtype=np.float32)},
    ),
    (
        {"input_1": np.ones((3, 2, 1), dtype=np.float32)},
        {"lambda": np.ones((3, 2, 1), dtype=np.float32)},
    ),
    (
        {"input_1": 2 * np.ones((3, 2, 1), dtype=np.float32)},
        {"lambda": 2 * np.ones((3, 2, 1), dtype=np.float32)},
    ),
    (
        {"input_1": 3 * np.ones((3, 2, 1), dtype=np.float32)},
        {"lambda": 3 * np.ones((3, 2, 1), dtype=np.float32)},
    ),
    (
        {"input_1": -1 * np.ones((3, 2, 1), dtype=np.float32)},
        {"lambda": np.zeros((3, 2, 1), dtype=np.float32)},
    ),
]


@skip_unless("ENABLE_TF_TEST", "True")
def test_tf_model_local_path(dummy_tf_models):
    DummyTFModel, *_ = dummy_tf_models
    model = DummyTFModel(
        asset_path=os.path.join(TEST_DIR, "testdata", "dummy_tf_model", "0.0"),
        model_settings={
            "output_dtypes": {"lambda": np.float32},
            "output_tensor_mapping": {"lambda": "nothing"},
            "output_shapes": {"lambda": (3, 2, 1)},
        },
    )
    v = np.zeros((3, 2, 1), dtype=np.float32)
    assert np.allclose(v, model({"input_1": v})["lambda"])


@skip_unless("ENABLE_TF_SERVING_TEST", "True")
@skip_unless("ENABLE_TF_TEST", "True")
def test_tf_model(monkeypatch, working_dir, dummy_tf_models):
    DummyTFModel, *_ = dummy_tf_models
    monkeypatch.setenv("MODELKIT_STORAGE_BUCKET", TEST_DIR)
    monkeypatch.setenv("MODELKIT_STORAGE_PREFIX", "testdata")
    monkeypatch.setenv("MODELKIT_STORAGE_PROVIDER", "local")
    monkeypatch.setenv("MODELKIT_ASSETS_DIR", working_dir)

    lib = ModelLibrary(models=DummyTFModel)
    assert not lib.settings.tf_serving.enable
    model = lib.get("dummy_tf_model")
    v = np.zeros((3, 2, 1), dtype=np.float32)
    assert np.allclose(v, model({"input_1": v})["lambda"])


@pytest.fixture(scope="function")
def tf_serving(request, monkeypatch, working_dir, dummy_tf_models):
    DummyTFModel, *_ = dummy_tf_models
    monkeypatch.setenv("MODELKIT_ASSETS_DIR", working_dir)
    monkeypatch.setenv("MODELKIT_STORAGE_BUCKET", TEST_DIR)
    monkeypatch.setenv("MODELKIT_STORAGE_PREFIX", "testdata")
    monkeypatch.setenv("MODELKIT_STORAGE_PROVIDER", "local")

    lib = ModelLibrary(models=DummyTFModel, settings={"lazy_loading": True})
    yield tf_serving_fixture(request, lib, tf_version="2.8.0")


@skip_unless("ENABLE_TF_SERVING_TEST", "True")
@skip_unless("ENABLE_TF_TEST", "True")
@pytest.mark.parametrize(
    "model_name, test_items",
    [
        ("dummy_tf_model", TEST_ITEMS_IS_EMPTY),
        ("dummy_tf_model_no_is_empty", TEST_ITEMS),
    ],
)
def test_iso_serving_mode(model_name, test_items, tf_serving, dummy_tf_models):
    # model_name = "dummy_tf_model"
    # Get the prediction service running TF with gRPC serving
    lib_serving_grpc = ModelLibrary(
        required_models=[model_name],
        settings=LibrarySettings(
            tf_serving={
                "enable": True,
                "port": 8500,
                "mode": "grpc",
                "host": "localhost",
            }
        ),
        models=dummy_tf_models,
    )
    model_grpc = lib_serving_grpc.get(model_name)

    lib_serving_rest = ModelLibrary(
        required_models=[model_name],
        settings=LibrarySettings(
            tf_serving={
                "enable": True,
                "port": 8501,
                "mode": "rest",
                "host": "localhost",
            }
        ),
        models=dummy_tf_models,
    )
    model_rest = lib_serving_rest.get(model_name)

    # Get the prediction service running TF as a library
    lib_tflib = ModelLibrary(
        required_models=[model_name],
        settings=LibrarySettings(),
        models=dummy_tf_models,
    )
    assert not lib_tflib.settings.tf_serving.enable
    model_tflib = lib_tflib.get(model_name)
    _compare_models(model_tflib, model_grpc, test_items)

    model_grpc.grpc_stub = None
    _compare_models(model_rest, model_grpc, test_items)
    assert model_grpc.grpc_stub

    lib_serving_rest.close()
    lib_serving_grpc.close()


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


def _compare_models(model0, model1, items_and_results, tolerance=1e-2):
    """compares two models in the following situations:
    - model0 per item vs. model1 per item
    - model0 batched vs. model1 batched
    - model0 per item vs. model0 batched
    """
    res_model0_per_item = []

    try:
        # Compare two models on single_predictions
        for item, result in items_and_results:
            res_model0 = model0.predict(item)
            res_model0_per_item.append(res_model0)
            res_model1 = model1.predict(item)
            assert compare_result(res_model0, result, tolerance)
            assert compare_result(res_model0, res_model1, tolerance)
    except AssertionError as e:
        raise AssertionError(f"Models differ on single items\n{e.args[0]}") from e

    items = [item for item, _ in items_and_results]
    try:
        # Compare two models in batches
        res_model0_items = model0.predict_batch(items)
        res_model1_items = model1.predict_batch(items)
        for k in range(len(items)):
            res_model0 = res_model0_items[k]
            res_model1 = res_model1_items[k]
            assert compare_result(res_model0, res_model1, tolerance)
    except AssertionError as e:
        raise AssertionError(f"Models differ on item batches\n{e.args[0]}") from e

    try:
        # Compare batched vs. computed with one item
        for k in range(len(items)):
            assert compare_result(
                res_model0_items[k], res_model0_per_item[k], tolerance
            )
    except AssertionError as e:
        raise AssertionError(
            f"Models predictions on single and batches differ\n{e.args[0]}"
        ) from e


@pytest.mark.asyncio
@skip_unless("ENABLE_TF_SERVING_TEST", "True")
@skip_unless("ENABLE_TF_TEST", "True")
async def test_iso_async(tf_serving, event_loop, dummy_tf_models):
    DummyTFModel, DummyTFModelAsync, _ = dummy_tf_models

    # Get the prediction service running TF with REST serving
    lib = ModelLibrary(
        required_models=["dummy_tf_model", "dummy_tf_model_async"],
        settings=LibrarySettings(
            tf_serving={
                "enable": True,
                "port": 8501,
                "mode": "rest",
                "host": "localhost",
            }
        ),
        models=[DummyTFModel, DummyTFModelAsync],
    )
    m_jt2s = lib.get("dummy_tf_model")
    async_m_jt2s = lib.get("dummy_tf_model_async")

    await _compare_models_async(m_jt2s, async_m_jt2s, TEST_ITEMS_IS_EMPTY)
    await lib.aclose()
    assert async_m_jt2s.aiohttp_session.closed


async def _compare_models_async(model, model_async, items_and_results, tolerance=1e-2):
    """compares two models in the following situations:
    - model0 per item vs. model1 per item
    - model0 batched vs. model1 batched
    - model0 per item vs. model0 batched
    """
    res_model0_per_item = []

    try:
        # Compare two models on single_predictions
        for item, result in items_and_results:
            res_model0 = model.predict(item)
            res_model0_per_item.append(res_model0)
            res_model1 = await model_async.predict(item)
            assert compare_result(res_model0, result, tolerance)
            assert compare_result(res_model0, res_model1, tolerance)
    except AssertionError as e:
        raise AssertionError(f"Models differ on single items\n{e.args[0]}") from e

    items = [item for item, _ in items_and_results]
    try:
        # Compare two models in batches
        res_model0_items = model.predict_batch(items)
        res_model1_items = await model_async.predict_batch(items)
        for k in range(len(items)):
            res_model0 = res_model0_items[k]
            res_model1 = res_model1_items[k]
            assert compare_result(res_model0, res_model1, tolerance)
    except AssertionError as e:
        raise AssertionError(f"Models differ on item batches\n{e.args[0]}") from e

    try:
        # Compare batched vs. computed with one item
        for k in range(len(items)):
            assert compare_result(
                res_model0_items[k], res_model0_per_item[k], tolerance
            )
    except AssertionError as e:
        raise AssertionError(
            f"Models predictions on single and batches differ\n{e.args[0]}"
        ) from e


@skip_unless("ENABLE_TF_TEST", "True")
def test_write_tf_serving_config(base_dir, assetsmanager_settings):
    write_config(os.path.join(base_dir, "test.config"), {"model0": "/some/path"})
    ref = testing.ReferenceText(os.path.join(TEST_DIR, "testdata"))
    with open(os.path.join(base_dir, "test.config")) as f:
        ref.assert_equal("test.config", f.read())


@skip_unless("ENABLE_TF_TEST", "True")
def test_iso_serving_mode_no_serving(dummy_tf_models, monkeypatch, working_dir):
    monkeypatch.setenv("MODELKIT_STORAGE_BUCKET", TEST_DIR)
    monkeypatch.setenv("MODELKIT_STORAGE_PREFIX", "testdata")
    monkeypatch.setenv("MODELKIT_STORAGE_PROVIDER", "local")
    monkeypatch.setenv("MODELKIT_ASSETS_DIR", working_dir)
    monkeypatch.setenv("MODELKIT_TF_SERVING_ATTEMPTS", 1)
    # Get the prediction service running TF with gRPC serving

    with pytest.raises(grpc.RpcError):
        ModelLibrary(
            required_models=["dummy_tf_model"],
            settings=LibrarySettings(
                tf_serving={
                    "enable": True,
                    "port": 8500,
                    "mode": "grpc",
                    "host": "localhost",
                }
            ),
            models=dummy_tf_models,
        )

    with pytest.raises(requests.exceptions.ConnectionError):
        ModelLibrary(
            required_models=["dummy_tf_model"],
            settings=LibrarySettings(
                tf_serving={
                    "enable": True,
                    "port": 8501,
                    "mode": "rest",
                    "host": "localhost",
                }
            ),
            models=dummy_tf_models,
        )
