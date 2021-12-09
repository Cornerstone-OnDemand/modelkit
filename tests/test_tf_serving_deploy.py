import os
import shutil
import tempfile

import pytest

from modelkit import testing
from modelkit.core.library import ModelLibrary
from modelkit.core.model import Model
from modelkit.core.models.tensorflow_model import TensorflowModel
from modelkit.utils.tensorflow import deploy_tf_models, write_config
from tests import TEST_DIR
from tests.conftest import skip_unless

np = pytest.importorskip("numpy")


@skip_unless("ENABLE_TF_SERVING_TEST", "True")
@skip_unless("ENABLE_TF_TEST", "True")
def test_write_config():
    models = {
        "model_a": "path/to/model_a",
        "model_b": "path/to/model_b",
    }
    with tempfile.TemporaryDirectory() as tmp_dir:
        write_config(os.path.join(tmp_dir, "config.config"), models, verbose=True)

        ref = testing.ReferenceText(os.path.join(TEST_DIR, "testdata"))
        with open(os.path.join(tmp_dir, "config.config")) as f:
            ref.assert_equal("write_config.config", f.read())


@skip_unless("ENABLE_TF_SERVING_TEST", "True")
@skip_unless("ENABLE_TF_TEST", "True")
def test_deploy_tf_models_no_asset():
    np = pytest.importorskip("numpy")

    class DummyTFModelNoAsset(TensorflowModel):
        CONFIGURATIONS = {
            "dummy_non_tf_model": {
                "model_settings": {
                    "output_dtypes": {"lambda": np.float32},
                    "output_tensor_mapping": {"lambda": "nothing"},
                    "output_shapes": {"lambda": (3, 2, 1)},
                }
            }
        }

    lib = ModelLibrary(models=DummyTFModelNoAsset, settings={"lazy_loading": True})
    with pytest.raises(ValueError):
        deploy_tf_models(lib, "local-docker")


@skip_unless("ENABLE_TF_SERVING_TEST", "True")
@skip_unless("ENABLE_TF_TEST", "True")
def test_deploy_tf_models_no_tf_model():
    class DummyNonTFModel(Model):
        CONFIGURATIONS = {"dummy_non_tf_model": {}}

    lib = ModelLibrary(models=DummyNonTFModel, settings={"lazy_loading": True})
    deploy_tf_models(lib, "local-docker")


@skip_unless("ENABLE_TF_SERVING_TEST", "True")
@skip_unless("ENABLE_TF_TEST", "True")
def test_deploy_tf_models(monkeypatch):
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

    with pytest.raises(ValueError):
        lib = ModelLibrary(models=[DummyTFModel], settings={"lazy_loading": True})
        deploy_tf_models(lib, "remote", "remote")

    ref = testing.ReferenceText(os.path.join(TEST_DIR, "testdata", "tf_configs"))
    with tempfile.TemporaryDirectory() as tmp_dir:
        monkeypatch.setenv("MODELKIT_ASSETS_DIR", tmp_dir)
        monkeypatch.setenv("MODELKIT_STORAGE_BUCKET", TEST_DIR)
        monkeypatch.setenv("MODELKIT_STORAGE_PREFIX", "testdata")
        monkeypatch.setenv("MODELKIT_STORAGE_PROVIDER", "local")

        shutil.copytree(
            os.path.join(TEST_DIR, "testdata"), os.path.join(tmp_dir, "testdata")
        )
        os.makedirs(os.path.join(tmp_dir, "testdata", "dummy_tf_model_sub", "0.0"))
        lib = ModelLibrary(models=[DummyTFModel], settings={"lazy_loading": True})
        deploy_tf_models(lib, "local-docker", "local-docker")
        with open(os.path.join(tmp_dir, "local-docker.config")) as f:
            ref.assert_equal("local-docker.config", f.read())

        deploy_tf_models(lib, "remote", "remote")
        with open(os.path.join(tmp_dir, "remote.config")) as f:
            config_data = f.read().replace(TEST_DIR, "STORAGE_BUCKET")
            ref.assert_equal("remote.config", config_data)

        # local process mode depends on the tmp dir above and the platform
        # hence it cannot be tested reliably
        deploy_tf_models(lib, "local-process", "local-process")
