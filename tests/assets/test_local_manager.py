import os
import tempfile

import pytest

from modelkit.assets import errors
from modelkit.assets.manager import LocalAssetsManager


def test_local_manager_no_versions():
    # This test makes sure that the AssetsManager is able to retrieve files
    # refered to by their paths relative to the working_dir
    with tempfile.TemporaryDirectory() as assets_dir:
        os.makedirs(os.path.join(assets_dir, "something", "else"))
        with open(os.path.join(assets_dir, "something", "else", "deep.txt"), "w") as f:
            f.write("OK")

        manager = LocalAssetsManager(assets_dir=assets_dir)
        res = manager.fetch_asset("something/else/deep.txt", return_info=True)
        assert res["path"] == os.path.join(assets_dir, "something", "else", "deep.txt")

        manager = LocalAssetsManager(assets_dir=assets_dir)
        res = manager.fetch_asset("something", return_info=True)
        assert res["path"] == os.path.join(assets_dir, "something")

        with open(os.path.join(assets_dir, "something.txt"), "w") as f:
            f.write("OK")
        res = manager.fetch_asset("something.txt", return_info=True)
        assert res["path"] == os.path.join(assets_dir, "something.txt")

        with pytest.raises(errors.LocalAssetVersionDoesNotExistError):
            res = manager.fetch_asset("something.txt:0.1", return_info=True)

        with pytest.raises(errors.LocalAssetVersionDoesNotExistError):
            res = manager.fetch_asset("something.txt:0", return_info=True)


def test_local_manager_with_versions():
    with tempfile.TemporaryDirectory() as assets_dir:
        os.makedirs(os.path.join(assets_dir, "something", "0.0"))
        os.makedirs(os.path.join(assets_dir, "something", "0.1"))
        os.makedirs(os.path.join(assets_dir, "something", "1.1", "subpart"))
        with open(
            os.path.join(assets_dir, "something", "1.1", "subpart", "deep.txt"), "w"
        ) as f:
            f.write("OK")

        manager = LocalAssetsManager(assets_dir=assets_dir)
        res = manager.fetch_asset("something:1.1[subpart/deep.txt]", return_info=True)
        assert res["path"] == os.path.join(
            assets_dir, "something", "1.1", "subpart", "deep.txt"
        )

        manager = LocalAssetsManager(assets_dir=assets_dir)
        res = manager.fetch_asset("something/1.1/subpart/deep.txt", return_info=True)
        assert res["path"] == os.path.join(
            assets_dir, "something", "1.1", "subpart", "deep.txt"
        )

        manager = LocalAssetsManager(assets_dir=assets_dir)
        res = manager.fetch_asset("something:0.0", return_info=True)
        assert res["path"] == os.path.join(assets_dir, "something", "0.0")

        manager = LocalAssetsManager(assets_dir=assets_dir)
        res = manager.fetch_asset("something:0", return_info=True)
        assert res["path"] == os.path.join(assets_dir, "something", "0.1")

        manager = LocalAssetsManager(assets_dir=assets_dir)
        res = manager.fetch_asset("something", return_info=True)
        assert res["path"] == os.path.join(assets_dir, "something", "1.1")
