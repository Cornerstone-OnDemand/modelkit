import os
import shutil

import pytest

from modelkit.assets import errors
from modelkit.assets.manager import AssetsManager
from modelkit.assets.remote import StorageProvider
from modelkit.assets.settings import AssetSpec
from tests import TEST_DIR


def test_local_manager_no_versions(working_dir):
    # This test makes sure that the AssetsManager is able to retrieve files
    # refered to by their paths relative to the working_dir
    os.makedirs(os.path.join(working_dir, "something", "else"))
    with open(os.path.join(working_dir, "something", "else", "deep.txt"), "w") as f:
        f.write("OK")

    # valid relative path to assets dir
    manager = AssetsManager(assets_dir=working_dir)
    res = manager.fetch_asset("something/else/deep.txt", return_info=True)
    assert res["path"] == os.path.join(working_dir, "something", "else", "deep.txt")

    # valid relative path to CWD
    manager = AssetsManager()
    res = manager.fetch_asset("README.md", return_info=True)
    assert res["path"] == os.path.join(os.getcwd(), "README.md")

    # valid relative path to CWD with assets dir
    manager = AssetsManager(assets_dir=working_dir)
    res = manager.fetch_asset("README.md", return_info=True)
    assert res["path"] == os.path.join(os.getcwd(), "README.md")

    # valid absolute path
    manager = AssetsManager(assets_dir=working_dir)
    res = manager.fetch_asset(os.path.join(os.getcwd(), "README.md"), return_info=True)
    assert res["path"] == os.path.join(os.getcwd(), "README.md")

    # valid relative path dir
    manager = AssetsManager(assets_dir=working_dir)
    res = manager.fetch_asset("something", return_info=True)
    assert res["path"] == os.path.join(working_dir, "something")

    with open(os.path.join(working_dir, "something.txt"), "w") as f:
        f.write("OK")
    res = manager.fetch_asset("something.txt", return_info=True)
    assert res["path"] == os.path.join(working_dir, "something.txt")

    with pytest.raises(errors.LocalAssetDoesNotExistError):
        res = manager.fetch_asset("something.txt:0.1", return_info=True)

    with pytest.raises(errors.LocalAssetDoesNotExistError):
        res = manager.fetch_asset("something.txt:0", return_info=True)

    with pytest.raises(errors.AssetDoesNotExistError):
        res = manager.fetch_asset("doesnotexist.txt", return_info=True)


def test_local_manager_with_versions(working_dir):
    os.makedirs(os.path.join(working_dir, "something", "0.0"))
    open(os.path.join(working_dir, "something", "0.0", ".SUCCESS"), "w").close()

    os.makedirs(os.path.join(working_dir, "something", "0.1"))
    open(os.path.join(working_dir, "something", "0.1", ".SUCCESS"), "w").close()

    os.makedirs(os.path.join(working_dir, "something", "1.1", "subpart"))
    with open(
        os.path.join(working_dir, "something", "1.1", "subpart", "deep.txt"), "w"
    ) as f:
        f.write("OK")
    open(os.path.join(working_dir, "something", "1.1", ".SUCCESS"), "w").close()

    manager = AssetsManager(assets_dir=working_dir)
    res = manager.fetch_asset("something:1.1[subpart/deep.txt]", return_info=True)
    assert res["path"] == os.path.join(
        working_dir, "something", "1.1", "subpart", "deep.txt"
    )

    manager = AssetsManager(assets_dir=working_dir)
    res = manager.fetch_asset("something/1.1/subpart/deep.txt", return_info=True)
    assert res["path"] == os.path.join(
        working_dir, "something", "1.1", "subpart", "deep.txt"
    )

    manager = AssetsManager(assets_dir=working_dir)
    res = manager.fetch_asset("something:0.0", return_info=True)
    assert res["path"] == os.path.join(working_dir, "something", "0.0")

    manager = AssetsManager(assets_dir=working_dir)
    res = manager.fetch_asset("something:0", return_info=True)
    assert res["path"] == os.path.join(working_dir, "something", "0.1")

    manager = AssetsManager(assets_dir=working_dir)
    res = manager.fetch_asset("something", return_info=True)
    assert res["path"] == os.path.join(working_dir, "something", "1.1")

    try:
        manager = AssetsManager()
        local_dir = os.path.join("tmp-local-asset", "1.0", "subpart")
        os.makedirs(local_dir)
        open(os.path.join("tmp-local-asset", "1.0", ".SUCCESS"), "w").close()

        shutil.copy("README.md", local_dir)

        res = manager.fetch_asset(
            "tmp-local-asset:1.0[subpart/README.md]", return_info=True
        )
        assert res["path"] == os.path.abspath(os.path.join(local_dir, "README.md"))

        res = manager.fetch_asset("tmp-local-asset", return_info=True)
        assert res["path"] == os.path.abspath(os.path.join(local_dir, ".."))

        abs_path_to_readme = os.path.join(os.path.abspath(local_dir), "README.md")
        res = manager.fetch_asset(abs_path_to_readme, return_info=True)
        assert res["path"] == abs_path_to_readme
    finally:
        shutil.rmtree("tmp-local-asset")


def test_local_manager_with_fetch(working_dir):
    os.makedirs(os.path.join(working_dir, "category", "asset"))
    with open(os.path.join(working_dir, "category", "asset", "0.0"), "w") as f:
        f.write("OK")

    manager = AssetsManager(
        assets_dir=working_dir,
        storage_provider=StorageProvider(
            provider="local",
            bucket=os.path.join(TEST_DIR, "testdata", "test-bucket"),
            prefix="assets-prefix",
        ),
    )

    res = manager.fetch_asset("category/asset:0.0", return_info=True)
    assert res["path"] == os.path.join(working_dir, "category", "asset", "0.0")

    res = manager.fetch_asset("category/asset:0", return_info=True)
    assert res["path"] == os.path.join(working_dir, "category", "asset", "0.1")

    res = manager.fetch_asset("category/asset", return_info=True)
    assert res["path"] == os.path.join(working_dir, "category", "asset", "1.0")


def test_local_manager_with_fetch_external_bucket(working_dir):

    # when using external bucket in production (s3/gcs) in production
    # but need to use some local asset for debug purpose with
    # MODELKIT_ASSETS_DIR = MODELKIT_STORAGE_BUCKET/MODELKIT_STORAGE_PREFIX
    # configuration

    modelkit_storage_bucket = working_dir
    modelkit_storage_prefix = "assets-prefix"
    modelkit_assets_dir = os.path.join(modelkit_storage_bucket, modelkit_storage_prefix)

    os.makedirs(os.path.join(modelkit_assets_dir, "category", "asset"))
    with open(os.path.join(modelkit_assets_dir, "category", "asset", "0.0"), "w") as f:
        f.write("OK")

    manager = AssetsManager(
        assets_dir=modelkit_assets_dir,
        storage_provider=StorageProvider(
            provider="local",
            prefix=modelkit_storage_prefix,
            bucket=modelkit_storage_bucket,
        ),
    )

    res = manager.fetch_asset("category/asset:0.0", return_info=True)
    assert res["path"] == os.path.join(modelkit_assets_dir, "category", "asset", "0.0")


def test_fetch_asset_version_no_storage_provider(working_dir):
    manager = AssetsManager(assets_dir=working_dir)
    asset_name = os.path.join("category", "asset")
    spec = AssetSpec(
        name=asset_name,
        major_version="0",
        minor_version="0",
    )
    version = "0.0"

    asset_dict = manager._fetch_asset_version(
        spec=spec,
        version=version,
        local_versions=[version],  # version in local version
        _force_download=False,
    )

    assert asset_dict == {
        "from_cache": True,
        "version": version,
        "path": os.path.join(working_dir, asset_name, version),
    }

    with pytest.raises(errors.StorageDriverError):
        manager._fetch_asset_version(
            spec=spec,
            version=version,
            local_versions=[version],  # version in local version
            _force_download=True,
        )

    with pytest.raises(errors.StorageDriverError):
        manager._fetch_asset_version(
            spec=spec,
            version=version,
            local_versions=[],  # version not in local version
            _force_download=True,
        )

    with pytest.raises(errors.LocalAssetDoesNotExistError):
        manager._fetch_asset_version(
            spec=spec,
            version=version,
            local_versions=[],  #  version not in local version
            _force_download=False,
        )


def test_fetch_asset_version_with_storage_provider(working_dir):

    manager = AssetsManager(
        assets_dir=working_dir,
        storage_provider=StorageProvider(
            provider="local",
            bucket=os.path.join(TEST_DIR, "testdata", "test-bucket"),
            prefix="assets-prefix",
        ),
    )
    asset_name = os.path.join("category", "asset")
    spec = AssetSpec(
        name=asset_name,
        major_version="0",
        minor_version="0",
    )
    version = "0.0"

    # no _has_succeeded cache => fetch
    asset_dict = manager._fetch_asset_version(
        spec=spec,
        version=version,
        local_versions=[version],  # version in local version
        _force_download=False,
    )

    del asset_dict["meta"]  #  fetch meta data
    assert asset_dict == {
        "from_cache": False,
        "version": version,
        "path": os.path.join(working_dir, asset_name, version),
    }

    #  cache
    asset_dict = manager._fetch_asset_version(
        spec=spec,
        version=version,
        local_versions=[version],  # version in local version
        _force_download=False,
    )

    assert asset_dict == {
        "from_cache": True,
        "version": version,
        "path": os.path.join(working_dir, asset_name, version),
    }

    #  cache but force download
    asset_dict = manager._fetch_asset_version(
        spec=spec,
        version=version,
        local_versions=[version],  # version in local version
        _force_download=True,
    )

    del asset_dict["meta"]  #  fetch meta data
    assert asset_dict == {
        "from_cache": False,
        "version": version,
        "path": os.path.join(working_dir, asset_name, version),
    }

    # download asset
    asset_dict = manager._fetch_asset_version(
        spec=spec,
        version=version,
        local_versions=[],  # version not in local version
        _force_download=True,
    )

    del asset_dict["meta"]  #  fetch meta data
    assert asset_dict == {
        "from_cache": False,
        "version": version,
        "path": os.path.join(working_dir, asset_name, version),
    }

    # download asset
    asset_dict = manager._fetch_asset_version(
        spec=spec,
        version=version,
        local_versions=[],  # version not in local version
        _force_download=False,
    )

    del asset_dict["meta"]  #  fetch meta data
    assert asset_dict == {
        "from_cache": False,
        "version": version,
        "path": os.path.join(working_dir, asset_name, version),
    }


def test_fetch_asset_version_with_sub_parts(working_dir):
    manager = AssetsManager(
        assets_dir=working_dir,
    )
    asset_name = os.path.join("category", "asset")
    sub_part = "sub_part"
    spec = AssetSpec(
        name=asset_name, major_version="0", minor_version="0", sub_part=sub_part
    )
    version = "0.0"

    # no _has_succeeded cache => fetch
    asset_dict = manager._fetch_asset_version(
        spec=spec,
        version=version,
        local_versions=[version],  # version in local version
        _force_download=False,
    )

    assert asset_dict == {
        "from_cache": True,
        "version": version,
        "path": os.path.join(working_dir, asset_name, version, sub_part),
    }
