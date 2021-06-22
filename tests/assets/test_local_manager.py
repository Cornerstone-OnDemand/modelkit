import os
import shutil

import pytest

from modelkit.assets import errors
from modelkit.assets.manager import AssetsManager
from tests import TEST_DIR


def test_local_manager_no_versions(working_dir):
    # This test makes sure that the AssetsManager is able to retrieve files
    # refered to by their paths relative to the working_dir
    os.makedirs(os.path.join(working_dir, "something", "else"))
    with open(os.path.join(working_dir, "something", "else", "deep.txt"), "w") as f:
        f.write("OK")

    manager = AssetsManager(assets_dir=working_dir)
    res = manager.fetch_asset("something/else/deep.txt", return_info=True)
    assert res["path"] == os.path.join(working_dir, "something", "else", "deep.txt")

    manager = AssetsManager()
    res = manager.fetch_asset("README.md", return_info=True)
    assert res["path"] == os.path.join(os.getcwd(), "README.md")

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
        remote_store={
            "driver": {
                "storage_provider": "local",
                "bucket": os.path.join(TEST_DIR, "testdata", "test-bucket"),
            },
            "storage_prefix": "assets-prefix",
        },
    )

    res = manager.fetch_asset("category/asset:0.0", return_info=True)
    assert res["path"] == os.path.join(working_dir, "category", "asset", "0.0")

    res = manager.fetch_asset("category/asset:0", return_info=True)
    assert res["path"] == os.path.join(working_dir, "category", "asset", "0.1")

    res = manager.fetch_asset("category/asset", return_info=True)
    assert res["path"] == os.path.join(working_dir, "category", "asset", "1.0")
