import os
import tempfile

from modelkit.assets.drivers.local import LocalStorageDriver
from modelkit.assets.settings import DriverSettings

test_path = os.path.dirname(os.path.realpath(__file__))


def test_local_driver_upload_download_delete():
    with tempfile.TemporaryDirectory() as bucket_path:
        driver_settings = DriverSettings(storage_provider="local", bucket=bucket_path)
        local_driver = LocalStorageDriver(driver_settings.settings)

        assert not local_driver.exists(bucket_path, "some/object")

        # put an object
        with tempfile.TemporaryDirectory() as tempd:
            with open(os.path.join(tempd, "name"), "w") as fsrc:
                fsrc.write("some contents")
            local_driver.upload_object(
                os.path.join(tempd, "name"), bucket_path, "some/object"
            )
        local_driver_file_path = os.path.join(
            driver_settings.settings.bucket, "some", "object"
        )
        assert os.path.isfile(local_driver_file_path)
        assert local_driver.exists(bucket_path, "some/object")

        # download an object
        with tempfile.TemporaryDirectory() as tempdir:
            temp_path = os.path.join(tempdir, "test")
            local_driver.download_object(bucket_path, "some/object", temp_path)
            with open(temp_path) as fdst:
                assert fdst.read() == "some contents"

        # delete the object
        local_driver.delete_object(bucket_path, "some/object")
        assert not os.path.isfile(local_driver_file_path)
