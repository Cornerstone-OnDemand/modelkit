import os

import pytest

from modelkit.assets.drivers.local import LocalStorageDriver
from modelkit.assets.manager import AssetsManager
from modelkit.assets.remote import UnknownDriverError
from modelkit.core.settings import LibrarySettings

test_path = os.path.dirname(os.path.realpath(__file__))


@pytest.mark.parametrize(
    "settings_dict, env_vars, valid, exception",
    [
        (
            {
                "assets_dir": test_path,
            },
            {},
            True,
            None,
        ),
        (
            {"assets_dir": test_path, "timeout": 20},
            {},
            True,
            None,
        ),
        (
            {},
            {
                "MODELKIT_ASSETS_DIR": test_path,
                "MODELKIT_ASSETS_TIMEOUT_S": "100",
            },
            True,
            None,
        ),
        (
            {"timeout": 20},
            {
                "MODELKIT_ASSETS_DIR": test_path,
            },
            True,
            None,
        ),
        (
            {"assets_dir": 20},
            {},
            False,
            FileNotFoundError,
        ),
        ({"assets_dir": test_path, "timeout": "abc"}, {}, False, ValueError),
        (
            {
                "assets_dir": "/some/path",
            },
            {},
            False,
            FileNotFoundError,
        ),
        (
            {
                "assets_dir": test_path,
            },
            {"MODELKIT_STORAGE_PROVIDER": "s3"},
            False,
            ValueError,
        ),
        (
            {
                "assets_dir": test_path,
            },
            {"MODELKIT_STORAGE_PROVIDER": "gcs"},
            False,
            ValueError,
        ),
        (
            {
                "assets_dir": test_path,
            },
            {"MODELKIT_STORAGE_PROVIDER": "local"},
            False,
            ValueError,
        ),
        (
            {
                "assets_dir": test_path,
            },
            {
                "MODELKIT_STORAGE_PROVIDER": "local",
                "MODELKIT_STORAGE_BUCKET": "/some/path",
            },
            False,
            FileNotFoundError,
        ),
        (
            {
                "assets_dir": test_path,
            },
            {
                "MODELKIT_STORAGE_PROVIDER": "blabla",
            },
            False,
            UnknownDriverError,
        ),
    ],
)
def test_assetsmanager_init(monkeypatch, settings_dict, env_vars, valid, exception):
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    if valid:
        AssetsManager(**settings_dict)
    else:
        with pytest.raises(exception):
            AssetsManager(**settings_dict)


def test_assetsmanager_minimal_provider(monkeypatch, working_dir):
    monkeypatch.setenv("MODELKIT_ASSETS_DIR", working_dir)
    monkeypatch.setenv("MODELKIT_STORAGE_PROVIDER", "local")

    manager = AssetsManager()
    assert not manager.storage_provider

    monkeypatch.setenv("MODELKIT_STORAGE_BUCKET", working_dir)
    manager = AssetsManager()
    assert manager.assets_dir == working_dir
    assert isinstance(manager.storage_provider.driver, LocalStorageDriver)
    assert manager.storage_provider.driver.bucket == working_dir


def test_assetsmanager_no_validation(monkeypatch, working_dir):
    monkeypatch.setenv("MODELKIT_ASSETS_DIR", working_dir)
    settings = LibrarySettings()
    assert settings.enable_validation
    monkeypatch.setenv("MODELKIT_ENABLE_VALIDATION", "False")
    settings = LibrarySettings()
    assert not settings.enable_validation


def test_assetsmanager_default():
    manager = AssetsManager()
    assert manager.assets_dir == os.getcwd()
    assert manager.storage_provider is None
