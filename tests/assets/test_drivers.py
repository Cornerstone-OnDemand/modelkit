import os
import tempfile

from modelkit.assets.drivers.local import LocalStorageDriver
from modelkit.assets.settings import DriverSettings
from tests.conftest import skip_unless


def _perform_driver_test(driver):
    assert not driver.exists(driver.bucket, "some/object")

    # put an object
    with tempfile.TemporaryDirectory() as tempd:
        with open(os.path.join(tempd, "name"), "w") as fsrc:
            fsrc.write("some contents")
        driver.upload_object(os.path.join(tempd, "name"), driver.bucket, "some/object")
    assert driver.exists(driver.bucket, "some/object")

    # download an object
    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = os.path.join(tempdir, "test")
        driver.download_object(driver.bucket, "some/object", temp_path)
        with open(temp_path) as fdst:
            assert fdst.read() == "some contents"

    # iterate objects
    assert [x for x in driver.iterate_objects(driver.bucket)] == ["some/object"]

    # delete the object
    driver.delete_object(driver.bucket, "some/object")
    assert not driver.exists(driver.bucket, "some/object")


def test_local_driver(local_assetsmanager):
    _perform_driver_test(local_assetsmanager.remote_assets_store.driver)


@skip_unless("ENABLE_GCS_TEST", "True")
def test_gcs_driver(gcs_assetsmanager):
    _perform_driver_test(gcs_assetsmanager.remote_assets_store.driver)


@skip_unless("ENABLE_S3_TEST", "True")
def test_s3_driver(s3_assetsmanager):
    _perform_driver_test(s3_assetsmanager.remote_assets_store.driver)
