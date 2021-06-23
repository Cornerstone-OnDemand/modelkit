import os
import re
import shutil
from typing import Optional, Union, cast

import filelock
from structlog import get_logger

from modelkit.assets import errors
from modelkit.assets.remote import RemoteAssetsStore
from modelkit.assets.settings import AssetsManagerSettings, AssetSpec
from modelkit.assets.versioning import (
    VERSION_RE,
    filter_versions,
    parse_version,
    sort_versions,
)
from modelkit.utils.logging import ContextualizedLogging

logger = get_logger(__name__)


class AssetFetchError(Exception):
    pass


def _success_file_path(local_path):
    if os.path.isdir(local_path):
        return os.path.join(local_path, ".SUCCESS")
    else:
        dirn, fn = os.path.split(local_path)
        return os.path.join(dirn, f".{fn}.SUCCESS")


def _has_succeeded(local_path):
    return os.path.exists(_success_file_path(local_path))


class AssetsManager:
    def __init__(self, **settings):
        if isinstance(settings, dict):
            settings = AssetsManagerSettings(**settings)
        self.assets_dir = settings.assets_dir
        self.timeout = settings.timeout

        self.remote_assets_store = None
        if settings.remote_store:
            try:
                self.remote_assets_store = RemoteAssetsStore(
                    **settings.remote_store.dict()
                )
                logger.debug(
                    "AssetsManager created with remote storage provider",
                    driver=self.remote_assets_store.driver,
                )
            except BaseException:
                # A remote store was parametrized, but it could not be instantiated
                logger.error(
                    "Failed to instantiate the requested remote storage provider"
                )
                raise
        else:
            logger.debug("AssetsManager created without a remote storage provider")

    def get_local_versions_info(self, name):
        if os.path.isdir(name):
            return sort_versions(
                d for d in os.listdir(name) if re.fullmatch(VERSION_RE, d)
            )
        else:
            return []

    def _fetch_asset(self, spec: AssetSpec, _force_download=False):
        with ContextualizedLogging(name=spec.name):
            local_name = os.path.join(self.assets_dir, *spec.name.split("/"))
            local_versions_list = self.get_local_versions_info(local_name)
            logger.debug("Local versions list", local_versions_list=local_versions_list)
            remote_versions_list = []
            if self.remote_assets_store and (
                not spec.major_version or not spec.minor_version
            ):
                remote_versions_list = self.remote_assets_store.get_versions_info(
                    spec.name
                )
                logger.debug(
                    "Fetched remote versions list",
                    remote_versions_list=remote_versions_list,
                )
            all_versions_list = sort_versions(
                list({x for x in local_versions_list + remote_versions_list})
            )
            if not spec.major_version and not spec.minor_version:
                logger.debug("Asset has no version information")
                # no version is specified
                if not all_versions_list:
                    # and none exist
                    # in this case, the asset spec is likely a relative or absolute
                    # path to a file/directory
                    if os.path.exists(local_name):
                        logger.debug(
                            "Asset is a valid local path relative to ASSETS_DIR",
                            local_name=local_name,
                        )
                        # if the asset spec resolves to MODELKIT_ASSETS_DIR/spec.name
                        return {"path": local_name}
                    elif os.path.exists(
                        os.path.join(os.getcwd(), *spec.name.split("/"))
                    ):
                        logger.debug(
                            "Asset is a valid relative local path",
                            local_name=os.path.exists(
                                os.path.join(os.getcwd(), *spec.name.split("/"))
                            ),
                        )
                        # if the assect spec resolves to cwd/spec.name
                        return {
                            "path": os.path.join(os.getcwd(), *spec.name.split("/"))
                        }
                    elif os.path.exists(spec.name):
                        logger.debug(
                            "Asset is a valid absolute local path",
                            local_name=os.path.exists(
                                os.path.join(os.getcwd(), *spec.name.split("/"))
                            ),
                        )
                        # if the asset spec is a valid absolute path
                        return {"path": spec.name}
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
                    major=spec.major_version,
                    minor=spec.minor_version,
                )

            version = f"{spec.major_version}.{spec.minor_version}"
            with ContextualizedLogging(version=version):
                local_path = os.path.join(
                    self.assets_dir, *spec.name.split("/"), version
                )
                if not _has_succeeded(local_path):
                    logger.info("Previous fetching of asset has failed, redownloading.")
                    _force_download = True
                if _force_download:
                    if os.path.exists(local_path):
                        if os.path.isdir(local_path):
                            shutil.rmtree(local_path)
                        else:
                            os.unlink(local_path)
                    success_object_path = _success_file_path(local_path)
                    if os.path.exists(success_object_path):
                        os.unlink(success_object_path)
                if not _force_download and (version in local_versions_list):
                    asset_dict = {
                        "from_cache": True,
                        "version": version,
                        "path": local_path,
                    }
                else:
                    if self.remote_assets_store:
                        logger.info(
                            "Fetching distant asset",
                            local_versions=local_versions_list,
                        )
                        asset_download_info = self.remote_assets_store.download(
                            spec.name, version, self.assets_dir
                        )
                        asset_dict = {
                            **asset_download_info,
                            "from_cache": False,
                            "version": version,
                            "path": local_path,
                        }
                        if os.path.isdir(local_path):
                            open(_success_file_path(local_path), "w").close()
                        else:
                            open(_success_file_path(local_path), "w").close()
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

            return asset_dict

    def fetch_asset(
        self,
        spec: Union[AssetSpec, str],
        return_info=False,
        force_download: Optional[bool] = None,
    ):
        if isinstance(spec, str):
            spec = cast(AssetSpec, AssetSpec.from_string(spec))
        if force_download is None and self.remote_assets_store:
            force_download = self.remote_assets_store.force_download

        logger.info(
            "Fetching asset",
            spec=spec,
            return_info=return_info,
            force_download=force_download,
        )

        lock_path = (
            os.path.join(self.assets_dir, ".cache", *spec.name.split("/")) + ".lock"
        )
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        with filelock.FileLock(lock_path, timeout=self.timeout):
            asset_info = self._fetch_asset(spec, _force_download=force_download)
        logger.debug("Fetched asset", spec=spec, asset_info=asset_info)
        path = asset_info["path"]
        if not os.path.exists(path):
            logger.error(
                "An unknown error occured when fetching asset."
                "The path does not exist.",
                path=path,
                spec=spec,
            )
            raise AssetFetchError(
                f"An unknown error occured when fetching asset {spec}."
                f"The path {path} does not exist."
            )
        if not return_info:
            return path
        return asset_info
