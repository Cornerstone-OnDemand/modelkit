import filecmp
import os
import tempfile
import uuid

import pytest

import modelkit.assets.cli
from modelkit.assets.manager import AssetsManager
from modelkit.assets.settings import DriverSettings

test_path = os.path.dirname(os.path.realpath(__file__))


def _perform_mng_test(mng):
    # test pushing a file asset
    data_path = os.path.join(test_path, "testdata", "some_data.json")
    mng.push_asset(data_path, "category-test/some-data.ext", "1.0")
    # check metadata
    meta = mng.get_asset_meta("category-test/some-data.ext", "1.0")
    assert not meta["is_directory"]
    # fetch asset
    d = mng._fetch_asset("category-test/some-data.ext", "1.0")
    fetched_path = d["path"]
    assert fetched_path.endswith(os.path.join("category-test/some-data.ext", "1.0"))

    # check that it was not fetched from cache
    assert not d["from_cache"]
    # and meta is present
    assert d["meta"]
    # compare
    assert filecmp.cmp(fetched_path, data_path)

    # test pushing a directory asset
    data_path = os.path.join(test_path, "testdata", "some_data_folder")
    mng.push_asset(data_path, "category-test/some-data-2", "1.0")

    # check metadata
    meta = mng.get_asset_meta("category-test/some-data-2", "1.0")
    assert meta["is_directory"]

    # fetch asset
    d = mng._fetch_asset("category-test/some-data-2", "1.0")
    fetched_path = d["path"]
    assert fetched_path.endswith(os.path.join("category-test/some-data-2", "1.0"))

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
    d = mng._fetch_asset("category-test/some-data.ext", "1.0")
    # check that it was fetched from cache
    assert d["from_cache"]
    # and meta is present
    assert d["meta"]

    # fetch asset again
    d = mng._fetch_asset("category-test/some-data-2", "1.0")
    # check that it was fetched from cache
    assert d["from_cache"]
    # and meta is present
    assert d["meta"]

    # attempt to overwrite the asset
    with pytest.raises(Exception):
        mng.push_asset(
            os.path.join(data_path, "some_data_in_folder.json"),
            "category-test/some-data.ext",
            "1.0",
        )

    # fetch asset again
    d = mng._fetch_asset("category-test/some-data.ext", "1.0")
    assert d["from_cache"]
    assert d["meta"]


def test_local_assetsmanager(local_assetsmanager):
    _perform_mng_test(local_assetsmanager)


@pytest.mark.skipif(
    os.environ.get("ENABLE_GCS", "False") == "False", reason="GCS not available"
)
def test_gcs_assetsmanager(gcs_assetsmanager):
    _perform_mng_test(gcs_assetsmanager)


@pytest.mark.skipif(
    os.environ.get("ENABLE_S3", "False") == "False", reason="S3 not available"
)
def test_s3_assetsmanager(s3_assetsmanager):
    _perform_mng_test(s3_assetsmanager)


@pytest.mark.skipif(
    "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ,
    reason="Service account not configured",
)
def test_gcs_service_account_path(working_dir):
    # We want to be able to specify a specific service account path in the settings,
    # without reading an implicit environment variable
    # Of course, in the tests, we only have an environment variable, but specifying it
    # explicitly allows to exercise the Client.service_account_json code path.
    driver_settings = DriverSettings(
        storage_provider="gcs",
        service_account_path=os.environ["GOOGLE_APPLICATION_CREDENTIALS"],
    )
    assert driver_settings.settings.service_account_path

    mng = AssetsManager(
        driver_settings=driver_settings,
        working_dir=working_dir,
        assetsmanager_prefix=f"test-assets-{uuid.uuid1().hex}",
    )
    assert list(mng.iterate_assets()) == []


@pytest.mark.skipif(
    os.environ.get("ENABLE_GCS", "False") == "False", reason="GCS not available"
)
def test_download_object_or_prefix_cli(gcs_assetsmanager):
    original_asset_path = os.path.join(test_path, "testdata", "some_data.json")

    gcs_asset_dir = (
        f"gs://{gcs_assetsmanager.bucket}/{gcs_assetsmanager.assetsmanager_prefix}"
        "/category-test/some-data.ext"
    )
    gcs_asset_path = gcs_asset_dir + "/1.0"

    gcs_assetsmanager.push_asset(
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
                    f"gs://{gcs_assetsmanager.bucket}/"
                    f"{gcs_assetsmanager.assetsmanager_prefix}/"
                    "category-test"
                ),
                destination_dir=tmp_dir,
            )
