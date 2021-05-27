import os
import re
from typing import Union, cast

import filelock

from modelkit.assets import errors
from modelkit.assets.log import logger
from modelkit.assets.remote import RemoteAssetsStore
from modelkit.assets.settings import AssetsManagerSettings, AssetSpec
from modelkit.assets.versioning import (
    VERSION_RE,
    filter_versions,
    parse_version,
    sort_versions,
)
from modelkit.logging.context import ContextualizedLogging


class AssetsManager:
    def __init__(self, **settings):
        if isinstance(settings, dict):
            settings = AssetsManagerSettings(**settings)
        self.assets_dir = settings.assets_dir

        self.remote_assets_store = None
        if settings.remote_store:
            self.remote_assets_store = RemoteAssetsStore(**settings.remote_store.dict())

    def get_local_versions_info(self, name):
        if os.path.isdir(name):
            return sort_versions(
                d for d in os.listdir(name) if re.fullmatch(VERSION_RE, d)
            )
        else:
            return []

    def _fetch_asset(self, spec: AssetSpec, return_info=False):
        local_name = os.path.join(self.assets_dir, *spec.name.split("/"))
        local_versions_list = self.get_local_versions_info(local_name)
        remote_versions_list = []
        if self.remote_assets_store and (
            not spec.major_version or not spec.minor_version
        ):
            remote_versions_list = self.remote_assets_store.get_versions_info(spec.name)
        all_versions_list = sort_versions(
            list({x for x in local_versions_list + remote_versions_list})
        )
        if not spec.major_version and not spec.minor_version:
            # no version is specified
            if not all_versions_list:
                # and none exist
                if os.path.exists(local_name):
                    return {"path": local_name}
                else:
                    raise errors.AssetDoesNotExistError(spec.name)

        if not spec.major_version or not spec.minor_version:
            if not all_versions_list:
                raise errors.LocalAssetDoesNotExistError(
                    name=spec.name,
                    major=spec.major_version,
                    minor=spec.minor_version,
                    local_versions=local_versions_list,
                )

            # at least one version info is missing, fetch the latest
            if not spec.major_version:
                spec.major_version, spec.minor_version = parse_version(
                    all_versions_list[0]
                )
            elif not spec.minor_version:
                spec.major_version, spec.minor_version = parse_version(
                    filter_versions(all_versions_list, major=spec.major_version)[0]
                )
            logger.debug(
                "Resolved latest version",
                name=spec.name,
                major=spec.major_version,
                minor=spec.minor_version,
            )

        version = f"{spec.major_version}.{spec.minor_version}"
        with ContextualizedLogging(name=spec.name, version=version):
            asset_dict = {
                "from_cache": True,
                "version": version,
                "path": os.path.join(self.assets_dir, *spec.name.split("/"), version),
            }
            if version not in local_versions_list:
                if self.remote_assets_store:
                    logger.info(
                        "Fetching distant asset",
                        local_versions=local_versions_list,
                    )
                    asset_download_info = self.remote_assets_store.download(
                        spec.name, version, self.assets_dir
                    )
                    asset_dict.update({**asset_download_info, "from_cache": False})
                else:
                    raise errors.LocalAssetDoesNotExistError(
                        name=spec.name,
                        major=spec.major_version,
                        minor=spec.minor_version,
                        local_versions=local_versions_list,
                    )
            if spec.sub_part:
                local_sub_part = os.path.join(
                    *(
                        list(os.path.split(str(asset_dict["path"])))
                        + [p for p in spec.sub_part.split("/") if p]
                    )
                )
                asset_dict["path"] = local_sub_part

        if return_info:
            return asset_dict
        else:
            return asset_dict["path"]

    def fetch_asset(self, spec: Union[AssetSpec, str], return_info=False):
        logger.info("Fetching asset", spec=spec, return_info=return_info)

        if isinstance(spec, str):
            spec = cast(AssetSpec, AssetSpec.from_string(spec))

        lock_path = (
            os.path.join(self.assets_dir, ".cache", *spec.name.split("/")) + ".lock"
        )
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        with filelock.FileLock(lock_path, timeout=5):
            return self._fetch_asset(spec, return_info=return_info)
