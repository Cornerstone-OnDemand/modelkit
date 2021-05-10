import filecmp
import os

import pytest

from tests import TEST_DIR


def _perform_mng_test_subpart(mng):
    # test a multi part asset
    data_path = os.path.join(TEST_DIR, "assets", "testdata", "some_data_folder")
    mng.new_asset(data_path, "category-test/some-data-subpart")

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
    mng.new_asset(data_path, "category-test/some-data-subpart-2")

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


@pytest.mark.skipif(
    os.environ.get("ENABLE_GCS", "False") == "False", reason="GCS not available"
)
def test_gcs_assetsmanager_subpart(gcs_assetsmanager):
    _perform_mng_test_subpart(gcs_assetsmanager)


def test_s3_assetsmanager_subpart(s3_assetsmanager):
    _perform_mng_test_subpart(s3_assetsmanager)
