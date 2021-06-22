import filecmp
import os
import tempfile

import pytest

import modelkit.assets.cli
from tests.conftest import skip_unless

test_path = os.path.dirname(os.path.realpath(__file__))


def _perform_mng_test(mng):
    # test pushing a file asset
    data_path = os.path.join(test_path, "testdata", "some_data.json")
    mng.remote_assets_store.push(data_path, "category-test/some-data.ext", "1.0")
    # check metadata
    meta = mng.remote_assets_store.get_asset_meta("category-test/some-data.ext", "1.0")
    assert not meta["is_directory"]
    # fetch asset
    d = mng.fetch_asset("category-test/some-data.ext:1.0", return_info=True)
    fetched_path = d["path"]
    assert fetched_path.endswith(os.path.join("category-test", "some-data.ext", "1.0"))

    # check that it was not fetched from cache
    assert not d["from_cache"]
    # and meta is present
    assert d["meta"]
    # compare
    assert filecmp.cmp(fetched_path, data_path)

    # test pushing a directory asset
    data_path = os.path.join(test_path, "testdata", "some_data_folder")
    mng.remote_assets_store.push(data_path, "category-test/some-data-2", "1.0")

    # check metadata
    meta = mng.remote_assets_store.get_asset_meta("category-test/some-data-2", "1.0")
    assert meta["is_directory"]

    # fetch asset
    d = mng.fetch_asset("category-test/some-data-2:1.0", return_info=True)
    fetched_path = d["path"]
    assert fetched_path.endswith(os.path.join("category-test", "some-data-2", "1.0"))

    # check that it was not fetched from cache
    assert not d["from_cache"]
    # and meta is present
    assert d["meta"]
    # compare
    assert not filecmp.cmpfiles(
        data_path,
        fetched_path,
        ["some_data_in_folder.json", "some_data_in_folder_2.json"],
        shallow=False,
    )[1]

    # fetch asset again
    d = mng.fetch_asset("category-test/some-data.ext:1.0", return_info=True)
    # check that it was fetched from cache
    assert d["from_cache"]

    # fetch asset again
    d = mng.fetch_asset("category-test/some-data-2:1.0", return_info=True)
    # check that it was fetched from cache
    assert d["from_cache"]

    # attempt to overwrite the asset
    with pytest.raises(Exception):
        mng.remote_assets_store.push(
            os.path.join(data_path, "some_data_in_folder.json"),
            "category-test/some-data.ext",
            "1.0",
        )

    # fetch asset again
    d = mng.fetch_asset("category-test/some-data.ext:1.0", return_info=True)
    assert d["from_cache"]


def test_local_assetsmanager(local_assetsmanager):
    _perform_mng_test(local_assetsmanager)


@skip_unless("ENABLE_GCS_TEST", "True")
def test_gcs_assetsmanager(gcs_assetsmanager):
    _perform_mng_test(gcs_assetsmanager)


@skip_unless("ENABLE_S3_TEST", "True")
def test_s3_assetsmanager(s3_assetsmanager):
    _perform_mng_test(s3_assetsmanager)


@skip_unless("ENABLE_GCS_TEST", "True")
def test_download_object_or_prefix_cli(gcs_assetsmanager):
    original_asset_path = os.path.join(test_path, "testdata", "some_data.json")
    gcs_asset_dir = (
        f"gs://{gcs_assetsmanager.remote_assets_store.bucket}/"
        f"{gcs_assetsmanager.remote_assets_store.prefix}"
        "/category-test/some-data.ext"
    )
    gcs_asset_path = gcs_asset_dir + "/1.0"

    gcs_assetsmanager.remote_assets_store.push(
        original_asset_path, "category-test/some-data.ext", "1.0"
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        asset_path = modelkit.assets.cli._download_object_or_prefix(
            gcs_assetsmanager, asset_path=gcs_asset_path, destination_dir=tmp_dir
        )
        assert filecmp.cmp(original_asset_path, asset_path)

    with tempfile.TemporaryDirectory() as tmp_dir:
        asset_dir = modelkit.assets.cli._download_object_or_prefix(
            gcs_assetsmanager, asset_path=gcs_asset_dir, destination_dir=tmp_dir
        )
        assert filecmp.cmp(original_asset_path, os.path.join(asset_dir, "1.0"))

    with tempfile.TemporaryDirectory() as tmp_dir:
        with pytest.raises(modelkit.assets.errors.ObjectDoesNotExistError):
            modelkit.assets.cli._download_object_or_prefix(
                gcs_assetsmanager,
                asset_path=gcs_asset_dir + "file-not-found",
                destination_dir=tmp_dir,
            )

        with pytest.raises(modelkit.assets.errors.ObjectDoesNotExistError):
            # fail because dir contains subdir
            modelkit.assets.cli._download_object_or_prefix(
                gcs_assetsmanager,
                asset_path=(
                    f"gs://{gcs_assetsmanager.remote_assets_store.bucket}/"
                    f"{gcs_assetsmanager.remote_assets_store.prefix}/"
                    "category-test"
                ),
                destination_dir=tmp_dir,
            )
