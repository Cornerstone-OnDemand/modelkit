import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from modelkit.assets.drivers.gcs import GCSDriverSettings
from modelkit.assets.drivers.local import LocalDriverSettings
from modelkit.assets.drivers.s3 import S3DriverSettings
from modelkit.assets.settings import (
    AssetsManagerSettings,
    DriverSettings,
    RemoteAssetsStoreSettings,
)
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
                "remote_store": {
                    "driver": {
                        "storage_provider": "local",
                        "bucket": test_path,
                    },
                    "storage_prefix": "assets-prefix",
                },
                "assets_dir": test_path,
            },
            True,
        ),
        (
            {
                "remote_store": {"driver": {"storage_provider": "gcs"}},
                "assets_dir": "/some/path",
            },
            False,
        ),
        (
            {
                "remote_store": {
                    "driver": {
                        "storage_provider": "gcs",
                        "bucket": "something-tests",
                    }
                },
                "assets_dir": test_path,
            },
            True,
        ),
        (
            {"remote_store": {"driver": {"storage_provider": "gcs"}}},
            False,
        ),
        (
            {
                "remote_store": {
                    "driver": {"storage_provider": "gcs"},
                    "other_field": "tests",
                }
            },
            False,
        ),
        ({"remote_store": {"driver": {"storage_provider": "local"}}}, False),
    ],
)
def test_assetsmanager_settings(monkeypatch, settings_dict, valid):
    if valid:
        assetsmanager_settings = AssetsManagerSettings(**settings_dict)
        assert isinstance(assetsmanager_settings, AssetsManagerSettings)
    else:
        with pytest.raises(ValidationError):
            AssetsManagerSettings(**settings_dict)


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
def test_remote_assets_store_settings(monkeypatch, settings_dict, valid):
    if valid:
        assetsmanager_settings = RemoteAssetsStoreSettings(**settings_dict)
        assert isinstance(assetsmanager_settings, RemoteAssetsStoreSettings)
    else:
        with pytest.raises(ValidationError):
            RemoteAssetsStoreSettings(**settings_dict)


def test_assetsmanager_minimal(monkeypatch, working_dir):
    monkeypatch.setenv("MODELKIT_ASSETS_DIR", working_dir)
    monkeypatch.setenv("MODELKIT_STORAGE_BUCKET", "some-bucket")
    monkeypatch.setenv("MODELKIT_STORAGE_PROVIDER", "gcs")
    settings = AssetsManagerSettings()
    assert settings.remote_store.driver.storage_provider == "gcs"
    assert settings.remote_store.driver.settings == GCSDriverSettings()
    assert settings.remote_store.driver.settings.bucket == "some-bucket"
    assert settings.remote_store.storage_prefix == "modelkit-assets"
    assert settings.assets_dir == Path(working_dir)


def test_assetsmanager_minimal_provider(monkeypatch, working_dir):
    monkeypatch.setenv("MODELKIT_ASSETS_DIR", working_dir)
    monkeypatch.setenv("MODELKIT_STORAGE_PROVIDER", "local")

    settings = AssetsManagerSettings()
    assert not settings.remote_store

    monkeypatch.setenv("MODELKIT_STORAGE_BUCKET", working_dir)
    settings = AssetsManagerSettings()
    assert settings.remote_store.driver.storage_provider == "local"
    assert settings.remote_store.driver.settings == LocalDriverSettings()
    assert settings.remote_store.driver.settings.bucket == Path(working_dir)
    assert settings.assets_dir == Path(working_dir)


def test_assetsmanager_minimal_prefix(monkeypatch, working_dir):
    monkeypatch.setenv("MODELKIT_ASSETS_DIR", working_dir)
    monkeypatch.setenv("MODELKIT_STORAGE_BUCKET", "some-bucket")
    monkeypatch.setenv("MODELKIT_STORAGE_PREFIX", "a-prefix")
    monkeypatch.setenv("MODELKIT_STORAGE_PROVIDER", "gcs")

    settings = AssetsManagerSettings()
    assert settings.remote_store.driver.storage_provider == "gcs"
    assert settings.remote_store.driver.settings == GCSDriverSettings()
    assert settings.remote_store.driver.settings.bucket == "some-bucket"
    assert settings.remote_store.storage_prefix == "a-prefix"
    assert settings.assets_dir == Path(working_dir)


def test_assetsmanager_no_validation(monkeypatch, working_dir):
    monkeypatch.setenv("MODELKIT_ASSETS_DIR", working_dir)
    settings = LibrarySettings()
    assert settings.enable_validation
    monkeypatch.setenv("MODELKIT_ENABLE_VALIDATION", "False")
    settings = LibrarySettings()
    assert not settings.enable_validation


def test_assetsmanager_default():
    settings = AssetsManagerSettings()
    assert settings.assets_dir == Path(os.getcwd())
    assert settings.remote_store is None


def test_assetsmanager_storage_provider_bug(monkeypatch):
    monkeypatch.setenv("STORAGE_PROVIDER", "gcs")
    monkeypatch.setenv("MODELKIT_STORAGE_PROVIDER", "s3")
    monkeypatch.setenv("MODELKIT_STORAGE_BUCKET", "some-bucket")
    settings = DriverSettings()
    assert settings.storage_provider == "s3"

    settings = AssetsManagerSettings()
    assert settings.remote_store.driver.storage_provider == "s3"
