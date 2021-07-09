import os
import tempfile

from modelkit import testing
from modelkit.utils.tensorflow import write_config
from tests import TEST_DIR


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
