import os
import tempfile

from modelkit.assets.drivers.local import LocalStorageDriver
from tests import TEST_DIR
from tests.conftest import skip_unless


def _perform_driver_test(driver):
    assert not driver.exists("some/object")

    # put an object
    with tempfile.TemporaryDirectory() as tempd:
        with open(os.path.join(tempd, "name"), "w") as fsrc:
            fsrc.write("some contents")
        driver.upload_object(os.path.join(tempd, "name"), "some/object")
    assert driver.exists("some/object")

    # download an object
    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = os.path.join(tempdir, "test")
        driver.download_object("some/object", temp_path)
        with open(temp_path) as fdst:
            assert fdst.read() == "some contents"

    # iterate objects
    assert [x for x in driver.iterate_objects()] == ["some/object"]

    # delete the object
    driver.delete_object("some/object")
    assert not driver.exists("some/object")


def test_local_driver(local_assetsmanager):
    _perform_driver_test(local_assetsmanager.storage_provider.driver)


@skip_unless("ENABLE_GCS_TEST", "True")
def test_gcs_driver(gcs_assetsmanager):
    _perform_driver_test(gcs_assetsmanager.storage_provider.driver)


@skip_unless("ENABLE_S3_TEST", "True")
def test_s3_driver(s3_assetsmanager):
    _perform_driver_test(s3_assetsmanager.storage_provider.driver)


@skip_unless("ENABLE_AZ_TEST", "True")
def test_az_driver(az_assetsmanager):
    _perform_driver_test(az_assetsmanager.storage_provider.driver)


def test_local_driver_overwrite(working_dir):
    driver = LocalStorageDriver(working_dir)
    driver.upload_object(
        os.path.join(TEST_DIR, "assets", "testdata", "some_data.json"), "a/b/c"
    )
    assert os.path.isfile(os.path.join(working_dir, "a", "b", "c"))
    # will remove the a/b/c file
    driver.upload_object(
        os.path.join(TEST_DIR, "assets", "testdata", "some_data.json"), "a/b/c"
    )
    assert os.path.isfile(os.path.join(working_dir, "a", "b", "c"))
    # will remove the a/b directory
    driver.upload_object(
        os.path.join(TEST_DIR, "assets", "testdata", "some_data.json"), "a/b"
    )
    assert os.path.isfile(os.path.join(working_dir, "a", "b"))
    # will remove the a/b file
    driver.upload_object(
        os.path.join(TEST_DIR, "assets", "testdata", "some_data.json"), "a/b/c"
    )
    assert os.path.isfile(os.path.join(working_dir, "a", "b", "c"))
