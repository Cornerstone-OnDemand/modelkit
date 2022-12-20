import os
import pickle
import tempfile
from typing import Optional

from modelkit.assets.drivers.abc import StorageDriver, StorageDriverSettings
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


def _perform_pickability_test(driver, monkeypatch):
    # check whether the driver is pickable when
    # no client is passed at instantation.
    # Hence the need to set driver's _client property to None
    monkeypatch.setattr(driver, "_client", None)
    assert pickle.dumps(driver)


def test_local_driver(local_assetsmanager):
    _perform_driver_test(local_assetsmanager.storage_provider.driver)


def test_local_driver_pickable(local_assetsmanager, monkeypatch):
    _perform_pickability_test(local_assetsmanager.storage_provider.driver, monkeypatch)


@skip_unless("ENABLE_GCS_TEST", "True")
def test_gcs_driver(gcs_assetsmanager):
    _perform_driver_test(gcs_assetsmanager.storage_provider.driver)


@skip_unless("ENABLE_GCS_TEST", "True")
def test_gcs_driver_pickable(gcs_assetsmanager, monkeypatch):
    _perform_pickability_test(gcs_assetsmanager.storage_provider.driver, monkeypatch)


@skip_unless("ENABLE_S3_TEST", "True")
def test_s3_driver(s3_assetsmanager):
    _perform_driver_test(s3_assetsmanager.storage_provider.driver)


@skip_unless("ENABLE_S3_TEST", "True")
def test_s3_driver_pickable(s3_assetsmanager, monkeypatch):
    _perform_pickability_test(s3_assetsmanager.storage_provider.driver, monkeypatch)


@skip_unless("ENABLE_AZ_TEST", "True")
def test_az_driver(az_assetsmanager):
    _perform_driver_test(az_assetsmanager.storage_provider.driver)


@skip_unless("ENABLE_AZ_TEST", "True")
def test_az_driver_pickable(az_assetsmanager, monkeypatch):
    _perform_pickability_test(az_assetsmanager.storage_provider.driver, monkeypatch)


def test_local_driver_overwrite(working_dir):
    driver = LocalStorageDriver(settings={"bucket": working_dir})
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


def test_storage_driver_client(monkeypatch):
    class MockedDriver(StorageDriver):
        @staticmethod
        def build_client(_):
            return {"built": True, "passed": False}

        def delete_object(self, object_name: str):
            ...

        def download_object(self, object_name: str, destination_path: str):
            ...

        def exists(self, object_name: str) -> bool:
            ...

        def upload_object(self, file_path: str, object_name: str):
            ...

        def get_object_uri(self, object_name: str, sub_part: Optional[str] = None):
            ...

        def iterate_objects(self, prefix: Optional[str] = None):
            ...

    # the storage provider should not build the client
    # since passed at instantiation
    settings = StorageDriverSettings(bucket="bucket")
    driver = MockedDriver(settings, client={"built": False, "passed": True})
    assert settings.lazy_driver is False
    assert driver._client is not None
    assert driver._client == driver.client == {"built": False, "passed": True}

    # the storage provider should build the client at init
    driver = MockedDriver(settings)
    assert settings.lazy_driver is False
    assert driver._client is not None
    assert driver._client == driver.client == {"built": True, "passed": False}

    monkeypatch.setenv("MODELKIT_LAZY_DRIVER", True)
    # the storage provider should not build the client eagerly nor store it
    # since MODELKIT_LAZY_DRIVER is set
    settings = StorageDriverSettings(bucket="bucket")
    driver = MockedDriver(settings)
    assert settings.lazy_driver is True
    assert driver._client is None
    # the storage provider builds it on-the-fly when accessed via the `client` property
    assert driver.client == {"built": True, "passed": False}
    # but does not store it
    assert driver._client is None

    # the storage provider should not build any client but use the one passed
    # at instantiation
    driver = MockedDriver(settings, client={"built": False, "passed": True})
    assert driver._client is not None
    assert driver._client == driver.client == {"built": False, "passed": True}
