import asyncio
import os
import tempfile

import pytest

from modelkit.assets.remote import StorageProvider
from tests import TEST_DIR


@pytest.fixture(scope="function")
def base_dir():
    with tempfile.TemporaryDirectory() as base_dir:
        yield base_dir


@pytest.fixture(scope="function")
def working_dir(base_dir):
    working_dir = os.path.join(base_dir, "working_dir")
    os.makedirs(working_dir)

    yield working_dir


@pytest.fixture
def assetsmanager_settings(working_dir):
    yield {
        "storage_provider": StorageProvider(
            prefix="assets-prefix",
            provider="local",
            bucket=os.path.join(TEST_DIR, "testdata", "test-bucket"),
        ),
        "assets_dir": working_dir,
    }


def clean_env():
    for env_var in [
        "MODELKIT_ASSETS_DIR",
        "MODELKIT_ASSETS_TIMEOUT_S",
        "MODELKIT_CACHE_HOST",
        "MODELKIT_CACHE_IMPLEMENTATION",
        "MODELKIT_CACHE_MAX_SIZE",
        "MODELKIT_CACHE_PORT",
        "MODELKIT_CACHE_PROVIDER",
        "MODELKIT_DEFAULT_PACKAGE",
        "MODELKIT_ENABLE_VALIDATION",
        "MODELKIT_LAZY_LOADING",
        "MODELKIT_STORAGE_BUCKET",
        "MODELKIT_STORAGE_FORCE_DOWNLOAD",
        "MODELKIT_STORAGE_PREFIX_OVERRIDE",
        "MODELKIT_STORAGE_PREFIX",
        "MODELKIT_STORAGE_PROVIDER",
        "MODELKIT_STORAGE_TIMEOUT_S",
        "MODELKIT_TF_SERVING_ATTEMPTS",
        "MODELKIT_TF_SERVING_ENABLE",
        "MODELKIT_TF_SERVING_MODE",
        "MODELKIT_TF_SERVING_PORT",
    ]:
        os.environ.pop(env_var, None)


def pytest_sessionstart(session):
    clean_env()


@pytest.fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


def skip_unless(var, value):
    env = os.environ.get(var)
    return pytest.mark.skipif(env != value, reason=f"{var} is not {value}")
