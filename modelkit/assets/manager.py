import os
import re
import shutil
from typing import Any, Dict, List, Optional, Union, cast

import filelock
from structlog import get_logger

from modelkit.assets import errors
from modelkit.assets.drivers.local import LocalStorageDriver
from modelkit.assets.remote import NoConfiguredProviderError, StorageProvider
from modelkit.assets.settings import AssetSpec
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
    assets_dir: str
    timeout: int
    storage_provider: Optional[StorageProvider]

    def __init__(
        self,
        assets_dir: Optional[str] = None,
        timeout: Optional[int] = None,
        storage_provider: Optional[StorageProvider] = None,
    ):
        self.assets_dir = (
            assets_dir or os.environ.get("MODELKIT_ASSETS_DIR") or os.getcwd()
        )
        if not os.path.isdir(self.assets_dir):
            raise FileNotFoundError(
                f"Assets directory {self.assets_dir} does not exist"
            )

        self.timeout: int = int(
            timeout or os.environ.get("MODELKIT_ASSETS_TIMEOUT_S") or 10
        )

        self.storage_provider = storage_provider
        if not self.storage_provider:
            try:
                self.storage_provider = StorageProvider()
                logger.debug(
                    "AssetsManager created with remote storage provider",
                    driver=self.storage_provider.driver,
                )
            except NoConfiguredProviderError:
                logger.info("No remote storage provider configured")

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
            local_versions = self.get_local_versions_info(local_name)
            logger.debug("Local versions", local_versions=local_versions)

            if spec.major_version and spec.minor_version:
                version = f"{spec.major_version}.{spec.minor_version}"
                with ContextualizedLogging(version=version):
                    return self._fetch_asset_version(
                        spec, version, local_versions, _force_download
                    )

            remote_versions = []
            if self.storage_provider:
                remote_versions = self.storage_provider.get_versions_info(spec.name)
                logger.debug("Fetched remote versions", remote_versions=remote_versions)

            all_versions = sort_versions(set(local_versions + remote_versions))

            if not all_versions:
                if not spec.major_version and not spec.minor_version:
                    logger.debug("Asset has no version information")
                    # no version is specified and none exist
                    # in this case, the asset spec is likely a relative or absolute
                    # path to a file/directory
                    return _fetch_local_version(spec.name, local_name)

                raise errors.LocalAssetDoesNotExistError(
                    name=spec.name,
                    major=spec.major_version,
                    minor=spec.minor_version,
                    local_versions=local_versions,
                )

            # at least one version info is missing, fetch the latest
            version = all_versions[0]
            if spec.major_version:  #  minor is missing
                version = filter_versions(all_versions, major=spec.major_version)[0]

            major, minor = parse_version(version)
            spec.major_version, spec.minor_version = str(major), str(minor)

            logger.debug("Resolved latest version", major=major, minor=minor)

            version = f"{spec.major_version}.{spec.minor_version}"
            with ContextualizedLogging(version=version):
                return self._fetch_asset_version(
                    spec, version, local_versions, _force_download
                )

    def _fetch_asset_version(
        self,
        spec: AssetSpec,
        version: str,
        local_versions: List[str],
        _force_download: bool,
    ) -> Dict[str, Any]:
        local_path = os.path.join(self.assets_dir, *spec.name.split("/"), version)

        if _force_download and not self.storage_provider:
            raise errors.StorageDriverError(
                "can not force_download with no storage provider"
            )

        if not _has_succeeded(local_path) and self.storage_provider:
            if isinstance(
                self.storage_provider.driver, LocalStorageDriver
            ) and self.assets_dir == os.path.join(
                self.storage_provider.driver.bucket,
                self.storage_provider.prefix,
            ):
                # prevent modelkit from deleting assets locally
                # if LocalStorageDriver configured as
                # MODELKIT_ASSETS_DIR = \
                #     MODELKIT_STORAGE_BUCKET/MODELKIT_STORAGE_PREFIX
                _force_download = False
            else:
                logger.info("Previous fetching of asset has failed, redownloading.")
                _force_download = True

        if _force_download and self.storage_provider:
            if os.path.exists(local_path):
                if os.path.isdir(local_path):
                    shutil.rmtree(local_path)
                else:
                    os.unlink(local_path)
            success_object_path = _success_file_path(local_path)
            if os.path.exists(success_object_path):
                os.unlink(success_object_path)

        if not _force_download and (version in local_versions):
            asset_dict = {
                "from_cache": True,
                "version": version,
                "path": local_path,
            }
        elif self.storage_provider:
            logger.info("Fetching distant asset", local_versions=local_versions)
            asset_download_info = self.storage_provider.download(
                spec.name, version, self.assets_dir
            )
            asset_dict = {
                **asset_download_info,
                "from_cache": False,
                "version": version,
                "path": local_path,
            }
            open(_success_file_path(local_path), "w").close()
        else:
            raise errors.LocalAssetDoesNotExistError(
                name=spec.name,
                major=spec.major_version,
                minor=spec.minor_version,
                local_versions=local_versions,
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
        force_download: bool = None,
    ):
        if isinstance(spec, str):
            spec = cast(AssetSpec, AssetSpec.from_string(spec))
        if force_download is None and self.storage_provider:
            force_download = self.storage_provider.force_download

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
        if not os.path.exists(path):  # pragma: no cover
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


def _fetch_local_version(asset_name: str, local_name: str) -> Dict[str, str]:
    if os.path.exists(local_name):
        logger.debug(
            "Asset is a valid local path relative to ASSETS_DIR",
            local_name=local_name,
        )
        # if the asset spec resolves to MODELKIT_ASSETS_DIR/asset_name
        return {"path": local_name}

    path = os.path.join(os.getcwd(), *asset_name.split("/"))
    if os.path.exists(path):
        logger.debug("Asset is a valid relative local path", local_name=path)
        # if the asset spec resolves to cwd/asset_name
        return {"path": path}

    if os.path.exists(asset_name):
        logger.debug("Asset is a valid absolute local path", local_name=path)
        # if the asset spec is a valid absolute path
        return {"path": asset_name}

    raise errors.AssetDoesNotExistError(asset_name)
