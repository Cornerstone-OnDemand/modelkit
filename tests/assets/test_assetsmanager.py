import filecmp
import os
import tempfile

import pytest

import modelkit.assets.cli
from modelkit.assets.manager import AssetsManager, _success_file_path
from modelkit.assets.remote import StorageProvider
from tests.conftest import skip_unless

test_path = os.path.dirname(os.path.realpath(__file__))


def _perform_mng_test(mng):
    # test pushing a file asset
    data_path = os.path.join(test_path, "testdata", "some_data.json")
    mng.storage_provider.push(data_path, "category-test/some-data.ext", "1.0")
    # check metadata
    meta = mng.storage_provider.get_asset_meta("category-test/some-data.ext", "1.0")
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
    mng.storage_provider.push(data_path, "category-test/some-data-2", "1.0")

    # check metadata
    meta = mng.storage_provider.get_asset_meta("category-test/some-data-2", "1.0")
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
        mng.storage_provider.push(
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


@skip_unless("ENABLE_AZ_TEST", "True")
def test_az_assetsmanager(az_assetsmanager):
    _perform_mng_test(az_assetsmanager)


@skip_unless("ENABLE_GCS_TEST", "True")
def test_download_object_or_prefix_cli(gcs_assetsmanager):
    original_asset_path = os.path.join(test_path, "testdata", "some_data.json")
    gcs_asset_dir = (
        f"gs://{gcs_assetsmanager.storage_provider.driver.bucket}/"
        f"{gcs_assetsmanager.storage_provider.prefix}"
        "/category-test/some-data.ext"
    )
    gcs_asset_path = gcs_asset_dir + "/1.0"

    gcs_assetsmanager.storage_provider.push(
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
                    f"gs://{gcs_assetsmanager.storage_provider.driver.bucket}/"
                    f"{gcs_assetsmanager.storage_provider.prefix}/"
                    "category-test"
                ),
                destination_dir=tmp_dir,
            )


def test_assetsmanager_force_download(monkeypatch, base_dir, working_dir):
    # Setup a bucket
    bucket_path = os.path.join(base_dir, "local_driver", "bucket")
    os.makedirs(bucket_path)

    mng = AssetsManager(
        assets_dir=working_dir,
        storage_provider=StorageProvider(provider="local", bucket=bucket_path),
    )
    data_path = os.path.join(test_path, "testdata", "some_data.json")
    mng.storage_provider.push(data_path, "category-test/some-data.ext", "1.0")

    asset_info = mng.fetch_asset("category-test/some-data.ext:1.0", return_info=True)
    assert not asset_info["from_cache"]

    asset_info_re = mng.fetch_asset("category-test/some-data.ext:1.0", return_info=True)
    assert asset_info_re["from_cache"]

    mng_force = AssetsManager(
        assets_dir=working_dir,
        storage_provider=StorageProvider(
            provider="local",
            bucket=bucket_path,
            force_download=True,
        ),
    )
    asset_info_force = mng_force.fetch_asset(
        "category-test/some-data.ext:1.0", return_info=True
    )
    assert not asset_info_force["from_cache"]

    monkeypatch.setenv("MODELKIT_STORAGE_FORCE_DOWNLOAD", "True")
    mng_force = AssetsManager(
        assets_dir=working_dir,
        storage_provider=StorageProvider(provider="local", bucket=bucket_path),
    )
    asset_info_force_env = mng_force.fetch_asset(
        "category-test/some-data.ext:1.0", return_info=True
    )
    assert not asset_info_force_env["from_cache"]


def test_assetsmanager_retry_on_fail(base_dir, working_dir):
    # Setup a bucket
    bucket_path = os.path.join(base_dir, "local_driver", "bucket")
    os.makedirs(bucket_path)

    mng = AssetsManager(
        assets_dir=working_dir,
        storage_provider=StorageProvider(
            provider="local",
            bucket=bucket_path,
        ),
    )
    # Try with a file asset
    data_path = os.path.join(test_path, "testdata", "some_data.json")
    mng.storage_provider.push(data_path, "category-test/some-data.ext", "1.0")

    asset_info = mng.fetch_asset("category-test/some-data.ext:1.0", return_info=True)
    assert not asset_info["from_cache"]
    assert os.path.exists(_success_file_path(asset_info["path"]))

    os.unlink(_success_file_path(asset_info["path"]))

    asset_info = mng.fetch_asset("category-test/some-data.ext:1.0", return_info=True)
    assert not asset_info["from_cache"]

    # Try with a directory asset
    data_path = os.path.join(test_path, "testdata")
    mng.storage_provider.push(data_path, "category-test/some-data-dir", "1.0")

    asset_info = mng.fetch_asset("category-test/some-data-dir:1.0", return_info=True)
    assert not asset_info["from_cache"]
    assert os.path.exists(_success_file_path(asset_info["path"]))

    os.unlink(_success_file_path(asset_info["path"]))

    asset_info = mng.fetch_asset("category-test/some-data-dir:1.0", return_info=True)
    assert not asset_info["from_cache"]
