import os

import pytest

from modelkit.assets import errors


def _perform_driver_error_object_not_found(driver):
    with pytest.raises(errors.ObjectDoesNotExistError):
        driver.download_object(driver.bucket, "someasset", "somedestination")
    assert not os.path.isfile("somedestination")


def test_local_driver(local_assetsmanager):
    local_driver = local_assetsmanager.storage_driver
    _perform_driver_error_object_not_found(local_driver)


@pytest.mark.skipif(
    os.environ.get("ENABLE_GCS", "False") == "False", reason="GCS not available"
)
def test_gcs_driver(gcs_assetsmanager):
    gcs_driver = gcs_assetsmanager.storage_driver
    _perform_driver_error_object_not_found(gcs_driver)


@pytest.mark.skipif(
    os.environ.get("ENABLE_S3", "False") == "False", reason="S3 not available"
)
def test_s3_driver(s3_assetsmanager):
    s3_driver = s3_assetsmanager.storage_driver
    _perform_driver_error_object_not_found(s3_driver)
