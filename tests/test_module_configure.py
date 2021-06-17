import os
import sys

from modelkit.core.model_configuration import configure
from tests import TEST_DIR
from tests.conftest import skip_unless


@skip_unless("ENABLE_TF_TEST", "True")
def test_configure_package():
    sys.path.append(os.path.join(TEST_DIR, "testdata"))
    confs = configure(models="test_module")
    assert len(confs) == 5


@skip_unless("ENABLE_TF_TEST", "True")
def test_configure_module():
    sys.path.append(os.path.join(TEST_DIR, "testdata"))
    confs = configure(models="test_module.module_a")
    assert len(confs) == 3
