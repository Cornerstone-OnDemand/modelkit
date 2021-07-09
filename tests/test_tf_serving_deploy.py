import os
import tempfile

import numpy as np
import pytest

from modelkit import testing
from modelkit.core.library import ModelLibrary
from modelkit.core.models.tensorflow_model import TensorflowModel
from modelkit.core.model import Model
from modelkit.utils.tensorflow import deploy_tf_models, write_config
from tests import TEST_DIR
from tests.conftest import skip_unless


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

