import os
import shutil
import stat

import pytest

from modelkit.assets import errors
from modelkit.assets.manager import AssetsManager, _fetch_local_version
from modelkit.assets.remote import StorageProvider
from modelkit.assets.settings import AssetSpec
from tests import TEST_DIR
from tests.assets.test_versioning import test_versioning


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


@pytest.mark.parametrize(
    "v00, v01, v11, v10, versioning",
    [
        ("0.0", "0.1", "1.0", "1.1", None),
        ("0.0", "0.1", "1.0", "1.1", "major_minor"),
        (
            "0000-00-00T00-00-00Z",
            "0000-00-00T01-00-00Z",
            "0000-00-00T10-00-00Z",
            "0000-00-00T11-00-00Z",
            "simple_date",
        ),
    ],
)
def test_local_manager_with_versions(
    v00, v01, v11, v10, versioning, working_dir, monkeypatch
):
    if versioning:
        monkeypatch.setenv("MODELKIT_ASSETS_VERSIONING_SYSTEM", versioning)

    os.makedirs(os.path.join(working_dir, "something", v00))
    open(os.path.join(working_dir, "something", v00, ".SUCCESS"), "w").close()

    os.makedirs(os.path.join(working_dir, "something", v01))
    open(os.path.join(working_dir, "something", v01, ".SUCCESS"), "w").close()

    os.makedirs(os.path.join(working_dir, "something", v11, "subpart"))
    with open(
        os.path.join(working_dir, "something", v11, "subpart", "deep.txt"), "w"
    ) as f:
        f.write("OK")
    open(os.path.join(working_dir, "something", v11, ".SUCCESS"), "w").close()

    manager = AssetsManager(assets_dir=working_dir)
    res = manager.fetch_asset(f"something:{v11}[subpart/deep.txt]", return_info=True)
    assert res["path"] == os.path.join(
        working_dir, "something", v11, "subpart", "deep.txt"
    )

    manager = AssetsManager(assets_dir=working_dir)
    res = manager.fetch_asset(f"something/{v11}/subpart/deep.txt", return_info=True)
    assert res["path"] == os.path.join(
        working_dir, "something", v11, "subpart", "deep.txt"
    )

    manager = AssetsManager(assets_dir=working_dir)
    res = manager.fetch_asset(f"something:{v00}", return_info=True)
    assert res["path"] == os.path.join(working_dir, "something", v00)

    manager = AssetsManager(assets_dir=working_dir)
    res = manager.fetch_asset("something", return_info=True)
    assert res["path"] == os.path.join(working_dir, "something", v11)

    if versioning in (None, "major_minor"):
        manager = AssetsManager(assets_dir=working_dir)
        res = manager.fetch_asset("something:0", return_info=True)
        assert res["path"] == os.path.join(working_dir, "something", v01)

    try:
        manager = AssetsManager()
        local_dir = os.path.join("tmp-local-asset", v10, "subpart")
        os.makedirs(local_dir)
        open(os.path.join("tmp-local-asset", v10, ".SUCCESS"), "w").close()

        shutil.copy("README.md", local_dir)

        res = manager.fetch_asset(
            f"tmp-local-asset:{v10}[subpart/README.md]", return_info=True
        )
        assert res["path"] == os.path.abspath(os.path.join(local_dir, "README.md"))

        res = manager.fetch_asset("tmp-local-asset", return_info=True)
        assert res["path"] == os.path.abspath(os.path.join(local_dir, ".."))

        abs_path_to_readme = os.path.join(os.path.abspath(local_dir), "README.md")
        res = manager.fetch_asset(abs_path_to_readme, return_info=True)
        assert res["path"] == abs_path_to_readme
    finally:
        shutil.rmtree("tmp-local-asset")


@pytest.mark.parametrize(*test_versioning.TWO_VERSIONING_PARAMETRIZE)
def test_local_manager_with_fetch(
    version_asset_name, version_1, version_2, versioning, working_dir, monkeypatch
):
    if versioning:
        monkeypatch.setenv("MODELKIT_ASSETS_VERSIONING_SYSTEM", versioning)

    manager = AssetsManager(
        assets_dir=working_dir,
        storage_provider=StorageProvider(
            provider="local",
            bucket=os.path.join(TEST_DIR, "testdata", "test-bucket"),
            prefix="assets-prefix",
        ),
    )

    res = manager.fetch_asset(
        f"category/{version_asset_name}:{version_1}", return_info=True
    )
    assert res["path"] == os.path.join(
        working_dir, "category", version_asset_name, version_1
    )

    res = manager.fetch_asset(f"category/{version_asset_name}", return_info=True)
    assert res["path"] == os.path.join(
        working_dir, "category", version_asset_name, version_2
    )

    if versioning in ["major_minor", None]:
        res = manager.fetch_asset(f"category/{version_asset_name}:0", return_info=True)
        assert res["path"] == os.path.join(
            working_dir, "category", version_asset_name, "0.1"
        )


def test_local_manager_invalid_configuration(working_dir):

    modelkit_storage_bucket = working_dir
    modelkit_storage_prefix = "assets-prefix"
    modelkit_assets_dir = os.path.join(modelkit_storage_bucket, modelkit_storage_prefix)
    os.makedirs(modelkit_assets_dir)

    with pytest.raises(errors.StorageDriverError):
        AssetsManager(
            assets_dir=modelkit_assets_dir,
            storage_provider=StorageProvider(
                provider="local",
                prefix=modelkit_storage_prefix,
                bucket=modelkit_storage_bucket,
            ),
        )


@pytest.mark.parametrize(*test_versioning.TWO_VERSIONING_PARAMETRIZE)
def test_read_only_manager_with_fetch(
    version_asset_name, version_1, version_2, versioning, base_dir, monkeypatch
):
    if versioning:
        monkeypatch.setenv("MODELKIT_ASSETS_VERSIONING_SYSTEM", versioning)

    # Prepare a read-only dir with raw assets
    working_dir = os.path.join(base_dir, "working-dir")
    shutil.copytree(
        os.path.join(TEST_DIR, "testdata", "test-bucket", "assets-prefix"), working_dir
    )
    os.chmod(working_dir, stat.S_IREAD | stat.S_IEXEC)

    try:
        manager = AssetsManager(
            assets_dir=working_dir,
            storage_provider=None,
        )

        res = manager.fetch_asset(
            f"category/{version_asset_name}:{version_1}", return_info=True
        )
        assert res["path"] == os.path.join(
            working_dir, "category", version_asset_name, version_1
        )

        res = manager.fetch_asset(f"category/{version_asset_name}", return_info=True)
        assert res["path"] == os.path.join(
            working_dir, "category", version_asset_name, version_2
        )

        if versioning in ["major_minor", None]:
            res = manager.fetch_asset(
                f"category/{version_asset_name}:0", return_info=True
            )
            assert res["path"] == os.path.join(
                working_dir, "category", version_asset_name, "0.1"
            )
    finally:
        os.chmod(working_dir, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)


@pytest.mark.parametrize(*test_versioning.INIT_VERSIONING_PARAMETRIZE)
def test_fetch_asset_version_no_storage_provider(
    version_asset_name, version, versioning
):
    manager = AssetsManager(
        assets_dir=os.path.join(TEST_DIR, "testdata", "test-bucket", "assets-prefix")
    )
    asset_name = os.path.join("category", version_asset_name)
    spec = AssetSpec(name=asset_name, version=version, versioning=versioning)

    asset_dict = manager._fetch_asset_version(
        spec=spec,
        _force_download=False,
    )
    assert asset_dict == {
        "from_cache": True,
        "version": version,
        "path": os.path.join(manager.assets_dir, asset_name, version),
    }

    with pytest.raises(errors.StorageDriverError):
        manager._fetch_asset_version(
            spec=spec,
            _force_download=True,
        )

    spec.name = os.path.join("not-existing-asset", version_asset_name)
    with pytest.raises(errors.LocalAssetDoesNotExistError):
        manager._fetch_asset_version(
            spec=spec,
            _force_download=False,
        )


@pytest.mark.parametrize(*test_versioning.INIT_VERSIONING_PARAMETRIZE)
def test_fetch_asset_version_with_storage_provider(
    version_asset_name, version, versioning, working_dir
):

    manager = AssetsManager(
        assets_dir=working_dir,
        storage_provider=StorageProvider(
            provider="local",
            bucket=os.path.join(TEST_DIR, "testdata", "test-bucket"),
            prefix="assets-prefix",
        ),
    )

    asset_name = os.path.join("category", version_asset_name)
    spec = AssetSpec(name=asset_name, version=version, versioning=versioning)

    # no _has_succeeded cache => fetch
    asset_dict = manager._fetch_asset_version(
        spec=spec,
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
        _force_download=True,
    )

    del asset_dict["meta"]  #  fetch meta data
    assert asset_dict == {
        "from_cache": False,
        "version": version,
        "path": os.path.join(working_dir, asset_name, version),
    }

    # Re-Download asset when missing version
    os.remove(os.path.join(working_dir, asset_name, version))
    asset_dict = manager._fetch_asset_version(
        spec=spec,
        _force_download=False,
    )

    del asset_dict["meta"]  #  fetch meta data
    assert asset_dict == {
        "from_cache": False,
        "version": version,
        "path": os.path.join(working_dir, asset_name, version),
    }


@pytest.mark.parametrize(*test_versioning.INIT_VERSIONING_PARAMETRIZE)
def test_fetch_asset_version_with_sub_parts(
    version_asset_name, version, versioning, working_dir
):
    manager = AssetsManager(
        assets_dir=os.path.join(TEST_DIR, "testdata", "test-bucket", "assets-prefix")
    )
    asset_name = os.path.join("category", version_asset_name)
    sub_part = "sub_part"
    spec = AssetSpec(
        name=asset_name, version=version, sub_part=sub_part, versioning=versioning
    )

    # no _has_succeeded cache => fetch
    asset_dict = manager._fetch_asset_version(
        spec=spec,
        _force_download=False,
    )

    assert asset_dict == {
        "from_cache": True,
        "version": version,
        "path": os.path.join(manager.assets_dir, asset_name, version, sub_part),
    }


def test_fetch_local_version():
    asset_name = os.path.join("category", "asset")
    local_name = os.path.join(
        TEST_DIR, "testdata", "test-bucket", "assets-prefix", asset_name
    )
    assert _fetch_local_version("", local_name) == {"path": local_name}
    assert _fetch_local_version("README.md", "") == {
        "path": os.path.join(os.getcwd(), "README.md")
    }
    asset_name = os.path.join(os.getcwd(), "README.md")
    assert _fetch_local_version(asset_name, "") == {"path": asset_name}

    with pytest.raises(errors.AssetDoesNotExistError):
        _fetch_local_version("asset/not/exists", "")
