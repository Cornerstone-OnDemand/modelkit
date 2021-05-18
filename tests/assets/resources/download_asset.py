#!/usr/bin/env python3
import os
import sys

import click

root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.append(root_dir)

from modelkit.assets.remote import RemoteAssetsStore  # NOQA  # isort:skip
from modelkit.assets.manager import AssetsManager  # NOQA  # isort:skip


@click.command()
@click.argument("assets_dir")
@click.argument("driver_path")
@click.argument("asset_name")
def download_asset(assets_dir, driver_path, asset_name):
    """
    Download the asset
    """
    am = AssetsManager(
        assets_dir=assets_dir,
        remote_store={
            "storage_driver": {
                "storage_provider": "local",
                "bucket": driver_path,
            },
            "assetsmanager_prefix": "prefix",
        },
    )
    asset_dict = am.fetch_asset(asset_name, return_info=True)
    if asset_dict["from_cache"]:
        print("__ok_from_cache__")
    else:
        print("__ok_not_from_cache__")


if __name__ == "__main__":
    download_asset()
