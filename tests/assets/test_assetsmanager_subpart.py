import filecmp
import os

from tests import TEST_DIR
from tests.conftest import skip_unless


def _perform_mng_test_subpart(mng):
    # test a multi part asset
    data_path = os.path.join(TEST_DIR, "assets", "testdata", "some_data_folder")
    mng.storage_provider.new(data_path, "category-test/some-data-subpart", "0.0")

    fetched_asset_dict = mng.fetch_asset(
        "category-test/some-data-subpart:0.0[/some_data_in_folder.json]",
        return_info=True,
    )
    assert filecmp.cmp(
        fetched_asset_dict["path"], os.path.join(data_path, "some_data_in_folder.json")
    )

    fetched_asset_dict = mng.fetch_asset(
        "category-test/some-data-subpart:0.0[some_data_in_folder.json]",
        return_info=True,
    )
    assert filecmp.cmp(
        fetched_asset_dict["path"], os.path.join(data_path, "some_data_in_folder.json")
    )

    fetched_asset_dict = mng.fetch_asset(
        "category-test/some-data-subpart:0.0[some_data_in_folder_2.json]",
        return_info=True,
    )
    assert filecmp.cmp(
        fetched_asset_dict["path"],
        os.path.join(data_path, "some_data_in_folder_2.json"),
    )

    # test a deeper directory structure
    data_path = os.path.join(TEST_DIR, "assets", "testdata")
    mng.storage_provider.new(data_path, "category-test/some-data-subpart-2", "0.0")

    fetched_asset_dict = mng.fetch_asset(
        "category-test/some-data-subpart-2:0.0[some_data.json]",
        return_info=True,
    )
    assert filecmp.cmp(
        fetched_asset_dict["path"],
        os.path.join(data_path, "some_data.json"),
    )
    fetched_asset_dict = mng.fetch_asset(
        "category-test/some-data-subpart-2:0.0"
        "[some_data_folder/some_data_in_folder_2.json]",
        return_info=True,
    )
    assert filecmp.cmp(
        fetched_asset_dict["path"],
        os.path.join(data_path, "some_data_folder", "some_data_in_folder_2.json"),
    )


def test_local_assetsmanager_subpart(local_assetsmanager):
    _perform_mng_test_subpart(local_assetsmanager)


@skip_unless("ENABLE_GCS_TEST", "True")
def test_gcs_assetsmanager_subpart(gcs_assetsmanager):
    _perform_mng_test_subpart(gcs_assetsmanager)


@skip_unless("ENABLE_S3_TEST", "True")
def test_s3_assetsmanager_subpart(s3_assetsmanager):
    _perform_mng_test_subpart(s3_assetsmanager)


@skip_unless("ENABLE_AZ_TEST", "True")
def test_az_assetsmanager_subpart(az_assetsmanager):
    _perform_mng_test_subpart(az_assetsmanager)
