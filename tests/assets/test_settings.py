import os
import tempfile
from pathlib import PosixPath

import pytest
from pydantic import ValidationError

from modelkit.assets.drivers.gcs import GCSDriverSettings
from modelkit.assets.drivers.local import LocalDriverSettings
from modelkit.assets.settings import AssetsManagerSettings, DriverSettings

test_path = os.path.dirname(os.path.realpath(__file__))


@pytest.mark.parametrize(
    "settings_dict, valid",
    [
        ({"storage_provider": "local"}, False),
        ({"storage_provider": "local", "some_other_param": "blabli"}, False),
        ({"storage_provider": "local", "bucket": test_path}, True),
    ],
)
def test_local_driver_settings(settings_dict, valid, monkeypatch):
    if "bucket" not in settings_dict:
        monkeypatch.delenv("ASSETS_BUCKET_NAME", raising=False)
    if valid:
        driver_settings = DriverSettings(**settings_dict)
        assert isinstance(driver_settings.settings, LocalDriverSettings)
    else:
        with pytest.raises(ValidationError):
            DriverSettings(**settings_dict)


@pytest.fixture
def clean_env(monkeypatch):
    monkeypatch.delenv("WORKING_DIR", raising=False)
    monkeypatch.delenv("ASSETS_BUCKET_NAME", raising=False)
    monkeypatch.delenv("ASSETS_PREFIX", raising=False)


@pytest.mark.parametrize(
    "settings_dict, valid",
    [
        (
            {
                "driver_settings": {"storage_provider": "gcs"},
                "working_dir": "/some/path",
            },
            False,
        ),
        (
            {
                "driver_settings": {
                    "storage_provider": "gcs",
                    "bucket": "something-tests",
                },
                "working_dir": "/",
            },
            True,
        ),
        (
            {"driver_settings": {"storage_provider": "gcs"}},
            False,
        ),
        (
            {"driver_settings": {"storage_provider": "gcs"}, "other_field": "tests"},
            False,
        ),
        ({"driver_settings": {"storage_provider": "local"}}, False),
    ],
)
def test_assetsmanager_settings(monkeypatch, clean_env, settings_dict, valid):
    if valid:
        assetsmanager_settings = AssetsManagerSettings(**settings_dict)
        assert isinstance(assetsmanager_settings, AssetsManagerSettings)
    else:
        with pytest.raises(ValidationError):
            AssetsManagerSettings(**settings_dict)


def test_assetsmanager_minimal(monkeypatch, clean_env):
    with tempfile.TemporaryDirectory() as working_dir:
        monkeypatch.setenv("WORKING_DIR", working_dir)
        monkeypatch.setenv("ASSETS_BUCKET_NAME", "some-bucket")
        monkeypatch.setenv("STORAGE_PROVIDER", "gcs")
        settings = AssetsManagerSettings()
        assert settings.driver_settings.storage_provider == "gcs"
        assert settings.driver_settings.settings == GCSDriverSettings()
        assert settings.driver_settings.settings.bucket == "some-bucket"
        assert settings.assetsmanager_prefix == "modelkit-assets"
        assert settings.working_dir == PosixPath(working_dir)


def test_assetsmanager_minimal_provider(monkeypatch, clean_env):
    with tempfile.TemporaryDirectory() as working_dir:
        monkeypatch.setenv("WORKING_DIR", working_dir)
        monkeypatch.setenv("STORAGE_PROVIDER", "local")
        with pytest.raises(ValidationError):
            AssetsManagerSettings()

        monkeypatch.setenv("ASSETS_BUCKET_NAME", working_dir)
        settings = AssetsManagerSettings()
        assert settings.driver_settings.storage_provider == "local"
        assert settings.driver_settings.settings == LocalDriverSettings()
        assert settings.driver_settings.settings.bucket == PosixPath(working_dir)
        assert settings.working_dir == PosixPath(working_dir)


def test_assetsmanager_minimal_prefix(monkeypatch, clean_env):
    with tempfile.TemporaryDirectory() as working_dir:
        monkeypatch.setenv("WORKING_DIR", working_dir)
        monkeypatch.setenv("ASSETS_BUCKET_NAME", "some-bucket")
        monkeypatch.setenv("ASSETS_PREFIX", "a-prefix")
        monkeypatch.setenv("STORAGE_PROVIDER", "gcs")

        settings = AssetsManagerSettings()
        assert settings.driver_settings.storage_provider == "gcs"
        assert settings.driver_settings.settings == GCSDriverSettings()
        assert settings.driver_settings.settings.bucket == "some-bucket"
        assert settings.assetsmanager_prefix == "a-prefix"
        assert settings.working_dir == PosixPath(working_dir)
