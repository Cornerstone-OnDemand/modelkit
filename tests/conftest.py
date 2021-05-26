import asyncio
import os
import tempfile

import pytest


@pytest.fixture(scope="function")
def base_dir():
    with tempfile.TemporaryDirectory() as base_dir:
        yield base_dir


@pytest.fixture(scope="function")
def working_dir(base_dir):
    working_dir = os.path.join(base_dir, "working_dir")
    os.makedirs(working_dir)

    yield working_dir


def clean_env():
    for env_var in [
        "ASSETS_DIR",
        "WORKING_DIR",
        "ASSETS_BUCKET_NAME",
        "STORAGE_PREFIX",
        "STORAGE_PROVIDER",
        "LAZY_LOADING",
        "ASSETSMANAGER_PREFIX",
        "ASSETSMANAGER_TIMEOUT_S",
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
