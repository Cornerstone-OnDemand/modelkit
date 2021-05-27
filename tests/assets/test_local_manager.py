import os

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
    os.makedirs(os.path.join(working_dir, "something", "0.1"))
    os.makedirs(os.path.join(working_dir, "something", "1.1", "subpart"))
    with open(
        os.path.join(working_dir, "something", "1.1", "subpart", "deep.txt"), "w"
    ) as f:
        f.write("OK")

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
