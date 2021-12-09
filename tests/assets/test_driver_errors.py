import os

import pytest

from modelkit.assets import errors
from tests.conftest import skip_unless


def _perform_driver_error_object_not_found(driver):
    with pytest.raises(errors.ObjectDoesNotExistError):
        driver.download_object("someasset", "somedestination")
    assert not os.path.isfile("somedestination")


def test_local_driver(local_assetsmanager):
    local_driver = local_assetsmanager.storage_provider.driver
    _perform_driver_error_object_not_found(local_driver)


@skip_unless("ENABLE_GCS_TEST", "True")
def test_gcs_driver(gcs_assetsmanager):
    gcs_driver = gcs_assetsmanager.storage_provider.driver
    _perform_driver_error_object_not_found(gcs_driver)


@skip_unless("ENABLE_S3_TEST", "True")
def test_s3_driver(s3_assetsmanager):
    s3_driver = s3_assetsmanager.storage_provider.driver
    _perform_driver_error_object_not_found(s3_driver)


@skip_unless("ENABLE_AZ_TEST", "True")
def test_az_driver(az_assetsmanager):
    az_driver = az_assetsmanager.storage_provider.driver
    _perform_driver_error_object_not_found(az_driver)
