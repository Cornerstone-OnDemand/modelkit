import filecmp
import os

import pytest

from modelkit.assets import errors
from tests.conftest import skip_unless

test_path = os.path.dirname(os.path.realpath(__file__))


def _perform_mng_test(mng):
    # test dry run for new asset
    data_path = os.path.join(test_path, "testdata", "some_data.json")
    mng.remote_assets_store.new(data_path, "category-test/some-data", dry_run=True)
    with pytest.raises(Exception):
        mng.fetch_asset("category-test/some-data")

    # test updating an inexistant asset
    data_path = os.path.join(test_path, "testdata", "some_data.json")
    with pytest.raises(errors.AssetDoesNotExistError):
        mng.remote_assets_store.update(data_path, "category-test/some-data")

    # create the asset
    mng.remote_assets_store.new(data_path, "category-test/some-data")
    # check metadata
    mng.remote_assets_store.get_asset_meta("category-test/some-data", "0.0")

    # test dry run for update asset
    mng.remote_assets_store.update(data_path, "category-test/some-data", dry_run=True)
    with pytest.raises(Exception):
        mng.fetch_asset("category-test/some-data:0.1")

    # update the asset
    mng.remote_assets_store.update(data_path, "category-test/some-data")

    # check that it is present
    mng.remote_assets_store.get_asset_meta("category-test/some-data", "0.1")

    # pushing via new fails
    with pytest.raises(errors.AssetAlreadyExistsError):
        mng.remote_assets_store.new(data_path, "category-test/some-data")

    # update a major version via update
    mng.remote_assets_store.update(
        data_path, "category-test/some-data", bump_major=True
    )

    # update a major version that does not exist
    with pytest.raises(errors.AssetMajorVersionDoesNotExistError):
        mng.remote_assets_store.update(data_path, "category-test/some-data", major="10")

    # check that it is present
    mng.remote_assets_store.get_asset_meta("category-test/some-data", "1.0")

    # fetch the pinned asset
    fetched_path = mng.fetch_asset("category-test/some-data:1.0")
    assert filecmp.cmp(fetched_path, data_path)
    # fetch the major version asset
    fetched_path = mng.fetch_asset("category-test/some-data:1")
    assert filecmp.cmp(fetched_path, data_path)
    # fetch the latest asset
    fetched_path = mng.fetch_asset("category-test/some-data")
    assert filecmp.cmp(fetched_path, data_path)

    # fetch the latest asset from cache with full info
    fetched_asset_dict = mng.fetch_asset("category-test/some-data", return_info=True)
    assert fetched_asset_dict["path"], fetched_path
    assert fetched_asset_dict["from_cache"] is True
    assert fetched_asset_dict["version"] == "1.0"

    assert list(mng.remote_assets_store.iterate_assets()) == [
        ("category-test/some-data", ["1.0", "0.1", "0.0"])
    ]

    # pushing via new works
    mng.remote_assets_store.update(data_path, "category-test/some-data", major="1")

    # check that it is present
    mng.remote_assets_store.get_asset_meta("category-test/some-data", "1.1")

    fetched_asset_dict = mng.fetch_asset("category-test/some-data", return_info=True)
    assert fetched_asset_dict["path"], fetched_path
    assert fetched_asset_dict["from_cache"] is False
    assert fetched_asset_dict["version"] == "1.1"

    assert list(mng.remote_assets_store.iterate_assets()) == [
        ("category-test/some-data", ["1.1", "1.0", "0.1", "0.0"]),
    ]


def test_local_assetsmanager_versioning(local_assetsmanager):
    _perform_mng_test(local_assetsmanager)


@skip_unless("ENABLE_GCS_TEST", "True")
def test_gcs_assetsmanager_versioning(gcs_assetsmanager):
    _perform_mng_test(gcs_assetsmanager)


@skip_unless("ENABLE_S3_TEST", "True")
def test_s3_assetsmanager_versioning(s3_assetsmanager):
    _perform_mng_test(s3_assetsmanager)
