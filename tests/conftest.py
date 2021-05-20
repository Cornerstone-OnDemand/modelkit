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


@pytest.fixture
def clean_env(monkeypatch):
    for env_var in [
        "ASSETS_DIR",
        "WORKING_DIR",
        "ASSETS_BUCKET_NAME",
        "STORAGE_PROVIDER",
        "ASSETSMANAGER_PREFIX",
        "ASSETSMANAGER_TIMEOUT_S",
    ]:
        monkeypatch.delenv(env_var, raising=False)


def pytest_addoption(parser):
    parser.addoption("--skipslow", action="store_true", help="skip slow tests")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--skipslow"):
        return
    skip_slow = pytest.mark.skip(reason="need --skipslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")


@pytest.fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


def skip_unless(var, value):
    env = os.environ.get(var)
    return pytest.mark.skipif(env != value, reason=f"{var} is not {value}")
