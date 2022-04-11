import os
import shutil
from typing import Any, Dict, List, Optional, Union, cast

import filelock
from structlog import get_logger

from modelkit.assets import errors
from modelkit.assets.drivers.local import LocalStorageDriver
from modelkit.assets.remote import NoConfiguredProviderError, StorageProvider
from modelkit.assets.settings import AssetSpec
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

        if (
            self.storage_provider
            and isinstance(self.storage_provider.driver, LocalStorageDriver)
            and self.assets_dir
            == os.path.join(
                self.storage_provider.driver.bucket,
                self.storage_provider.prefix,
            )
        ):
            raise errors.StorageDriverError(
                "Incompatible configuration: LocalStorageDriver and AssetDir are "
                "pointing to the same folder. If assets are already downloaded,"
                "consider removing storage provider configuration."
            )

    def _fetch_asset(self, spec: AssetSpec, _force_download=False):
        with ContextualizedLogging(name=spec.name):

            self._resolve_version(spec)
            with ContextualizedLogging(version=spec.version):
                logger.debug("Resolved latest version", version=spec.version)
                return self._fetch_asset_version(spec, _force_download)

    def _resolve_version(self, spec: AssetSpec) -> None:
        local_versions = self._list_local_versions(spec)
        logger.debug("Local versions", local_versions=local_versions)

        if spec.is_version_complete():
            return

        remote_versions = []
        if self.storage_provider:
            remote_versions = self.storage_provider.get_versions_info(spec.name)
            logger.debug("Fetched remote versions", remote_versions=remote_versions)

        all_versions = spec.sort_versions(
            version_list=set(local_versions + remote_versions)
        )

        if not all_versions:
            if not spec.version:
                logger.debug("Asset has no version information")
                # no version is specified and none exist
                # in this case, the asset spec is likely a relative or absolute
                # path to a file/directory
                return None

            raise errors.LocalAssetDoesNotExistError(
                name=spec.name,
                version=spec.version,
                local_versions=local_versions,
            )

        # at least one version info is missing, update to the latest
        spec.set_latest_version(all_versions)

    def _fetch_asset_version(
        self,
        spec: AssetSpec,
        _force_download: bool,
    ) -> Dict[str, Any]:
        local_path = os.path.join(
            self.assets_dir, *spec.name.split("/"), spec.version or ""
        )

        if not spec.version:
            return _fetch_local_version(
                spec.name, os.path.join(self.assets_dir, *spec.name.split("/"))
            )

        if not self.storage_provider:

            if _force_download:
                raise errors.StorageDriverError(
                    "can not force_download with no storage provider"
                )
            local_versions = self._list_local_versions(spec)
            if spec.version not in local_versions:
                raise errors.LocalAssetDoesNotExistError(
                    name=spec.name,
                    version=spec.version,
                    local_versions=local_versions,
                )

            asset_dict = {
                "from_cache": True,
                "version": spec.version,
                "path": local_path,
            }

        else:

            # Ensure assets are not downloaded concurrently
            lock_path = (
                os.path.join(self.assets_dir, ".cache", *spec.name.split("/")) + ".lock"
            )
            os.makedirs(os.path.dirname(lock_path), exist_ok=True)
            with filelock.FileLock(lock_path, timeout=self.timeout):

                # Update local versions after lock aquisition to account for concurrent
                # download
                local_versions = self._list_local_versions(spec)

                if not _has_succeeded(local_path):
                    logger.info("Previous fetching of asset has failed, redownloading.")
                    _force_download = True

                if not _force_download and (spec.version in local_versions):
                    asset_dict = {
                        "from_cache": True,
                        "version": spec.version,
                        "path": local_path,
                    }
                else:

                    if _force_download:
                        if os.path.exists(local_path):
                            if os.path.isdir(local_path):
                                shutil.rmtree(local_path)
                            else:
                                os.unlink(local_path)
                        success_object_path = _success_file_path(local_path)
                        if os.path.exists(success_object_path):
                            os.unlink(success_object_path)

                    logger.info("Fetching distant asset", local_versions=local_versions)
                    asset_download_info = self.storage_provider.download(
                        spec.name, spec.version, self.assets_dir
                    )
                    asset_dict = {
                        **asset_download_info,
                        "from_cache": False,
                        "version": spec.version,
                        "path": local_path,
                    }
                    open(_success_file_path(local_path), "w").close()

        if spec.sub_part:
            local_sub_part = os.path.join(
                *(
                    list(os.path.split(str(asset_dict["path"])))
                    + [p for p in spec.sub_part.split("/") if p]
                )
            )
            asset_dict["path"] = local_sub_part
        return asset_dict

    def _list_local_versions(self, spec: AssetSpec) -> List[str]:
        local_name = os.path.join(self.assets_dir, *spec.name.split("/"))
        return spec.get_local_versions(local_name)

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
