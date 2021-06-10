import os
import sys

from modelkit.core.model_configuration import configure
from tests import TEST_DIR


def test_configure_package():
    sys.path.append(os.path.join(TEST_DIR, "testdata"))
    confs = configure(models="test_module")
    assert len(confs) == 5


def test_configure_module():
    sys.path.append(os.path.join(TEST_DIR, "testdata"))
    confs = configure(models="test_module.module_a")
    assert len(confs) == 3
