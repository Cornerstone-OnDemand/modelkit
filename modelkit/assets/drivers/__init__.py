from modelkit.assets.drivers.gcs import GCSStorageDriver
from modelkit.assets.drivers.local import LocalStorageDriver
from modelkit.assets.drivers.s3 import S3StorageDriver


def settings_to_driver(driver_settings):
    if driver_settings.storage_provider == "gcs":
        return GCSStorageDriver(driver_settings.settings)
    if driver_settings.storage_provider == "s3":
        return S3StorageDriver(driver_settings.settings)
    if driver_settings.storage_provider == "local":
        return LocalStorageDriver(driver_settings.settings)
