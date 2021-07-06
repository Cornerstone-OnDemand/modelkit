import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from modelkit.assets.drivers.gcs import GCSDriverSettings
from modelkit.assets.drivers.local import LocalDriverSettings, LocalStorageDriver
from modelkit.assets.drivers.s3 import S3DriverSettings
from modelkit.assets.manager import AssetsManager
from modelkit.assets.settings import DriverSettings, StorageProviderSettings
from modelkit.core.settings import LibrarySettings

test_path = os.path.dirname(os.path.realpath(__file__))


@pytest.mark.parametrize(
    "settings_dict, valid, expected_type",
    [
        ({"storage_provider": "notsupported"}, False, None),
        ({"storage_provider": "local"}, False, None),
        ({"storage_provider": "local", "some_other_param": "blabli"}, False, None),
        ({"storage_provider": "local", "bucket": test_path}, True, LocalDriverSettings),
        ({"storage_provider": "gcs", "bucket": test_path}, True, GCSDriverSettings),
        ({"storage_provider": "s3", "bucket": test_path}, True, S3DriverSettings),
    ],
)
def test_driver_settings(settings_dict, valid, expected_type):
    if valid:
        driver_settings = DriverSettings(**settings_dict)
        assert isinstance(driver_settings.settings, expected_type)
    else:
        with pytest.raises(ValidationError):
            DriverSettings(**settings_dict)


@pytest.mark.parametrize(
    "settings_dict, valid",
    [
        (
            {
                "assets_dir": test_path,
            },
            True,
        ),
        (
            {
                "assets_dir": "/some/path",
            },
            False,
        ),
    ],
)
def test_assetsmanager_init(settings_dict, valid):
    if valid:
        AssetsManager(**settings_dict)
    else:
        with pytest.raises(FileNotFoundError):
            AssetsManager(**settings_dict)


@pytest.mark.parametrize(
    "settings_dict, valid",
    [
        (
            {
                "storage_prefix": "assets-v3",
                "driver": {"storage_provider": "local", "bucket": test_path},
            },
            True,
        ),
        (
            {
                "storage_prefix": "assets-v3",
                "driver": {
                    "storage_provider": "local",
                    "settings": {"bucket": test_path},
                },
                "timeout_s": 300.0,
            },
            True,
        ),
    ],
)
def test_storage_provider_settings(monkeypatch, settings_dict, valid):
    if valid:
        assetsmanager_settings = StorageProviderSettings(**settings_dict)
        assert isinstance(assetsmanager_settings, StorageProviderSettings)
    else:
        with pytest.raises(ValidationError):
            StorageProviderSettings(**settings_dict)


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


def test_assetsmanager_storage_provider_bug(monkeypatch):
    monkeypatch.setenv("STORAGE_PROVIDER", "gcs")
    monkeypatch.setenv("MODELKIT_STORAGE_PROVIDER", "s3")
    monkeypatch.setenv("MODELKIT_STORAGE_BUCKET", "some-bucket")
    settings = DriverSettings()
    assert settings.storage_provider == "s3"
