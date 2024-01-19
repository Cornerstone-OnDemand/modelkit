import pydantic
import pytest

from modelkit.assets.drivers.abc import StorageDriverSettings
from modelkit.assets.drivers.azure import AzureStorageDriverSettings
from modelkit.assets.drivers.gcs import GCSStorageDriverSettings
from modelkit.assets.drivers.local import LocalStorageDriverSettings
from modelkit.assets.drivers.s3 import S3StorageDriverSettings
from modelkit.core.settings import ModelkitSettings


def test_modelkit_settings_working(monkeypatch):
    class ServingSettings(ModelkitSettings):
        enable: bool = pydantic.Field(
            False,
            validation_alias=pydantic.AliasChoices(
                "enable",
                "SERVING_ENABLE",
            ),
        )

    assert ServingSettings().enable is False
    assert ServingSettings(enable=True).enable is True

    monkeypatch.setenv("SERVING_ENABLE", "True")
    assert ServingSettings().enable is True
    # without ModelkitSettings, the following would raise a ValidationError
    # because both `enable` and `SERVING_ENABLE` are set and passed to the
    # constructor.
    assert ServingSettings(enable=False).enable is False


@pytest.mark.parametrize(
    "Settings",
    [
        StorageDriverSettings,
        GCSStorageDriverSettings,
        AzureStorageDriverSettings,
        S3StorageDriverSettings,
        LocalStorageDriverSettings,
    ],
)
def test_storage_driver_settings(Settings, monkeypatch):
    monkeypatch.setenv("MODELKIT_STORAGE_BUCKET", "foo")
    assert Settings().bucket == "foo"
    assert Settings(bucket="bar").bucket == "bar"
    monkeypatch.delenv("MODELKIT_STORAGE_BUCKET")
    assert Settings(bucket="bar").bucket == "bar"
    with pytest.raises(pydantic.ValidationError):
        _ = Settings()
