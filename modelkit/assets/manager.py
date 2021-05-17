import datetime
import glob
import json
import os
import re
import tempfile
import time
from typing import Union, cast

import filelock
import humanize
from dateutil import parser, tz

from modelkit.assets import errors, utils
from modelkit.assets.drivers import settings_to_driver
from modelkit.assets.log import logger
from modelkit.assets.settings import AssetsManagerSettings, AssetSpec
from modelkit.assets.versioning import (
    VERSION_RE,
    MajorVersionDoesNotExistError,
    filter_versions,
    increment_version,
    parse_version,
    sort_versions,
)
from modelkit.logging.context import ContextualizedLogging


def meta_file_serializer(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    return obj


class AssetsManager:
    def __init__(self, **kwargs):
        settings = AssetsManagerSettings(**kwargs)

        self.storage_driver = settings_to_driver(settings.driver_settings)
        if self.storage_driver:
            self.bucket = self.storage_driver.bucket

            self.timeout = settings.timeout_s
            self.working_dir = settings.working_dir
            self.assetsmanager_prefix = settings.assetsmanager_prefix

    def get_object_name(self, name, version):
        return "/".join((self.assetsmanager_prefix, name, version))

    def get_meta_object_name(self, name, version):
        return self.get_object_name(name, version) + ".meta"

    def get_versions_object_name(self, name):
        return "/".join((self.assetsmanager_prefix, name + ".versions"))

    def get_versions_info(self, name):
        """
        Retrieve asset versions information
        """
        versions_object_name = self.get_versions_object_name(name)
        versions_object_path = os.path.join(
            self.working_dir, self.assetsmanager_prefix, name + ".version"
        )
        os.makedirs(os.path.dirname(versions_object_path), exist_ok=True)
        self.storage_driver.download_object(
            self.bucket, versions_object_name, versions_object_path
        )
        with open(versions_object_path) as f:
            versions_list = json.load(f)["versions"]
        return versions_list

    def get_asset_meta(self, name, version):
        """
        Retrieve asset metadata
        """
        meta_object_name = self.get_meta_object_name(name, version)
        with tempfile.TemporaryDirectory() as tempdir:
            fdst = os.path.join(tempdir, "meta.tmp")
            self.storage_driver.download_object(self.bucket, meta_object_name, fdst)
            with open(fdst) as f:
                meta = json.load(f)
            meta["push_date"] = parser.isoparse(meta["push_date"])
        return meta

    def new_asset(self, asset_path, name, dry_run=False):
        """
        Upload a new asset
        """
        versions_object_name = self.get_versions_object_name(name)
        if self.storage_driver.exists(self.bucket, versions_object_name):
            raise errors.AssetAlreadyExistsError(name)
        logger.info(
            "Pushing new asset",
            name=name,
            asset_path=asset_path,
        )
        self.push_asset(asset_path, name, "0.0", dry_run=dry_run)

        with tempfile.TemporaryDirectory() as dversions:
            with open(os.path.join(dversions, "versions.json"), "w") as f:
                json.dump({"versions": ["0.0"]}, f)
            logger.debug(
                "Pushing versions file",
                bucket=self.bucket,
                name=name,
            )
            if not dry_run:
                self.storage_driver.upload_object(
                    os.path.join(dversions, "versions.json"),
                    self.bucket,
                    versions_object_name,
                )

    def update_asset(
        self, asset_path, name, bump_major=False, major=None, dry_run=False
    ):
        """
        Update an existing asset version
        """
        versions_object_name = self.get_versions_object_name(name)
        if not self.storage_driver.exists(self.bucket, versions_object_name):
            raise errors.AssetDoesNotExistError(name)
        logger.info(
            "Updating asset",
            name=name,
            major=major,
            asset_path=asset_path,
        )
        versions_list = self.get_versions_info(name)

        try:
            new_version = increment_version(
                versions_list, major=major, bump_major=bump_major
            )
        except MajorVersionDoesNotExistError:
            raise errors.AssetMajorVersionDoesNotExistError(name, major)

        self.push_asset(asset_path, name, new_version, dry_run=dry_run)

        with tempfile.TemporaryDirectory() as tmp_dir:
            versions_fn = os.path.join(tmp_dir, "versions.json")
            versions = sort_versions([new_version] + versions_list)
            with open(versions_fn, "w") as f:
                json.dump({"versions": versions}, f)
            logger.debug(
                "Pushing updated versions file",
                bucket=self.bucket,
                name=name,
                versions=versions,
            )
            if not dry_run:
                self.storage_driver.upload_object(
                    versions_fn, self.bucket, versions_object_name
                )

    def push_asset(self, asset_path, name, version, dry_run=False):
        """
        Push asset
        """
        with ContextualizedLogging(
            bucket=self.bucket,
            name=name,
            version=version,
            asset_path=asset_path,
        ):
            logger.info("Pushing asset")

            object_name = self.get_object_name(name, version)
            if self.storage_driver.exists(self.bucket, object_name):
                raise Exception(
                    f"`{name}` already exists, cannot"
                    f" overwrite asset for version `{version}`"
                )

            meta = {
                "push_date": datetime.datetime.now(tz.UTC).isoformat(),
                "is_directory": os.path.isdir(asset_path),
            }
            if meta["is_directory"]:
                asset_path += "/" if not asset_path.endswith("/") else ""
                meta["contents"] = sorted(
                    f[len(asset_path) :]
                    for f in glob.iglob(
                        os.path.join(asset_path, "**/*"), recursive=True
                    )
                    if os.path.isfile(f)
                )
                logger.info(
                    "Pushing multi-part asset file",
                    n_parts=len(meta["contents"]),
                )
                for part_no, part in enumerate(meta["contents"]):
                    path_to_push = os.path.join(asset_path, part)
                    remote_object_name = "/".join(
                        x
                        for x in object_name.split("/") + list(os.path.split(part))
                        if x
                    )
                    logger.debug(
                        "Pushing multi-part asset file",
                        object_name=remote_object_name,
                        path_to_push=path_to_push,
                        part=part,
                        part_no=part_no,
                        n_parts=len(meta["contents"]),
                    )
                    if not dry_run:
                        self.storage_driver.upload_object(
                            path_to_push, self.bucket, remote_object_name
                        )
                logger.info(
                    "Pushed multi-part asset file",
                    n_parts=len(meta["contents"]),
                )
            else:
                logger.info(
                    "Pushing asset file",
                    object_name=object_name,
                )
                if not dry_run:
                    self.storage_driver.upload_object(
                        asset_path, self.bucket, object_name
                    )

            with tempfile.TemporaryDirectory(dir=self.working_dir) as tmp_dir:
                meta_file_path = os.path.join(tmp_dir, "asset.meta")
                with open(meta_file_path, "w", encoding="utf-8") as fmeta:
                    json.dump(meta, fmeta, default=meta_file_serializer)

                logger.debug(
                    "Pushing meta file",
                    meta=meta,
                    bucket=self.bucket,
                    meta_object_name=object_name + ".meta",
                )
                if not dry_run:
                    self.storage_driver.upload_object(
                        meta_file_path, self.bucket, object_name + ".meta"
                    )

    def fetch_asset(self, spec: Union[AssetSpec, str], return_info=False):
        """
        Retrieves the asset and returns the local path to the asset in the working_dir
        """
        logger.info("Fetching asset", spec=spec, return_info=return_info)

        if isinstance(spec, str):
            spec = cast(AssetSpec, AssetSpec.from_string(spec))

        if not spec.major_version or not spec.minor_version:
            versions_list = self.get_versions_info(spec.name)
            if not spec.major_version:
                spec.major_version, spec.minor_version = parse_version(versions_list[0])
            elif not spec.minor_version:
                spec.major_version, spec.minor_version = parse_version(
                    filter_versions(versions_list, major=spec.major_version)[0]
                )

        version = f"{spec.major_version}.{spec.minor_version}"

        lock_path = (
            os.path.join(
                self.working_dir,
                self.assetsmanager_prefix,
                ".cache",
                spec.name,
                version,
            )
            + ".lock"
        )
        # Download remote asset with lock
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        with filelock.FileLock(lock_path, timeout=self.timeout):
            asset_dict = self._fetch_asset(spec.name, version, spec.sub_part)
        if return_info:
            return {
                **asset_dict,
                "version": version,
                "object_name": self.get_object_name(spec.name, version),
                "meta_object_name": self.get_meta_object_name(spec.name, version),
                "versions_object_name": self.get_versions_object_name(spec.name),
            }
        else:
            return asset_dict["path"]

    def _fetch_asset(self, name, version, sub_part=None):
        """
        Retrieves the asset and returns a dictionary with meta information, asset
        origin (from cache) and local path
        """
        with ContextualizedLogging(name=name, version=version):
            cache_asset_path = os.path.join(
                self.working_dir, self.assetsmanager_prefix, *name.split("/"), version
            )
            meta_path = cache_asset_path + ".meta"
            local_asset_path = os.path.join(
                self.working_dir, self.assetsmanager_prefix, *name.split("/"), version
            )
            object_name = self.get_object_name(name, version)

            if os.path.isfile(meta_path):
                with open(meta_path) as f:
                    meta = json.load(f)
                    meta["push_date"] = parser.isoparse(meta["push_date"])

                logger.info("Using local asset version")
                if sub_part:
                    local_sub_part = os.path.join(
                        *(
                            list(os.path.split(local_asset_path))
                            + [p for p in sub_part.split("/") if p]
                        )
                    )
                    return {
                        "path": local_sub_part,
                        "base_asset_path": local_asset_path,
                        "from_cache": True,
                        "meta": meta,
                    }
                return {"path": local_asset_path, "from_cache": True, "meta": meta}

            # Local file not found, retrieve the meta
            meta = self.get_asset_meta(name, version)

            if meta.get("is_directory"):
                logger.info(
                    "Downloading remote multi-part asset",
                    n_parts=len(meta["contents"]),
                )
                t0 = time.monotonic()
                for part_no, part in enumerate(meta["contents"]):
                    destination_path = os.path.join(
                        local_asset_path, os.path.join(*part.split("/"))
                    )
                    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
                    remote_part_name = "/".join(
                        x for x in object_name.split("/") + part.split("/") if x
                    )
                    logger.debug(
                        "Downloading asset part",
                        part_no=part_no,
                        n_parts=len(meta["contents"]),
                    )
                    self.storage_driver.download_object(
                        self.bucket, remote_part_name, destination_path
                    )
                    size = utils.get_size(destination_path)
                    logger.debug(
                        "Downloaded asset part",
                        part_no=part_no,
                        n_parts=len(meta["contents"]),
                        size=humanize.naturalsize(size),
                        size_bytes=size,
                    )
                size = utils.get_size(local_asset_path)
                logger.info(
                    "Downloaded remote multi-part asset",
                    size=humanize.naturalsize(size),
                    size_bytes=size,
                )
            else:
                logger.info("Downloading remote asset")
                t0 = time.monotonic()
                os.makedirs(os.path.dirname(local_asset_path), exist_ok=True)
                self.storage_driver.download_object(
                    self.bucket, object_name, local_asset_path
                )
                size = utils.get_size(local_asset_path)
                download_time = time.monotonic() - t0
                logger.info(
                    "Downloaded asset",
                    size=humanize.naturalsize(size),
                    time=humanize.naturaldelta(
                        datetime.timedelta(seconds=download_time)
                    ),
                    time_seconds=download_time,
                    size_bytes=size,
                )

            os.makedirs(os.path.dirname(meta_path), exist_ok=True)
            # Invalidate previous local meta and rewrite
            with open(meta_path, "w") as fmeta:
                json.dump(meta, fmeta, default=meta_file_serializer)

            # return
            if sub_part:
                local_sub_part = os.path.join(
                    local_asset_path, *(x for x in sub_part.split("/") if x)
                )
                return {
                    "path": local_sub_part,
                    "base_asset_path": local_asset_path,
                    "from_cache": True,
                    "meta": meta,
                }
            return {"path": local_asset_path, "from_cache": False, "meta": meta}

    def iterate_assets(self):
        assets_set = set()
        for asset_path in self.storage_driver.iterate_objects(
            self.bucket, self.assetsmanager_prefix
        ):
            if asset_path.endswith(".versions"):
                asset_name = "/".join(
                    asset_path[
                        len(self.assetsmanager_prefix) + 1 : -len(".versions")
                    ].split("/")
                )
                assets_set.add(asset_name)
        for asset_name in sorted(assets_set):
            versions_list = self.get_versions_info(asset_name)
            yield (asset_name, versions_list)


class LocalAssetsManager:
    def __init__(self, assets_dir):
        self.assets_dir = assets_dir

    def get_local_versions_info(self, name):
        if os.path.isdir(name):
            return sort_versions(
                d
                for d in os.listdir(name)
                if os.path.isdir(os.path.join(name, d)) and re.fullmatch(VERSION_RE, d)
            )
        else:
            return []

    def fetch_asset(self, spec: Union[AssetSpec, str], return_info=False):
        logger.info("Fetching asset", spec=spec, return_info=return_info)

        if isinstance(spec, str):
            spec = cast(AssetSpec, AssetSpec.from_string(spec))

        local_name = os.path.join(self.assets_dir, *spec.name.split("/"))
        versions_list = self.get_local_versions_info(local_name)
        if not spec.major_version and not spec.minor_version:
            # no version is specified
            if not versions_list:
                # and none exist
                return {"path": local_name}

        if not spec.major_version or not spec.minor_version:
            if not versions_list:
                raise errors.LocalAssetVersionDoesNotExistError(
                    name=spec.name, major=spec.major_version, minor=spec.minor_version
                )

            # at least one version info is missing, fetch the latest
            if not spec.major_version:
                spec.major_version, spec.minor_version = parse_version(versions_list[0])
            elif not spec.minor_version:
                spec.major_version, spec.minor_version = parse_version(
                    filter_versions(versions_list, major=spec.major_version)[0]
                )

        version = f"{spec.major_version}.{spec.minor_version}"
        if version not in versions_list:
            raise errors.LocalAssetVersionDoesNotExistError(
                name=spec.name, major=spec.major_version, minor=spec.minor_version
            )

        with ContextualizedLogging(name=spec.name, version=version):
            local_path = os.path.join(self.assets_dir, *spec.name.split("/"), version)
            if spec.sub_part:
                local_sub_part = os.path.join(
                    *(
                        list(os.path.split(local_path))
                        + [p for p in spec.sub_part.split("/") if p]
                    )
                )
                asset_dict = {
                    "path": local_sub_part,
                }
            else:
                asset_dict = {"path": local_path}
        if return_info:
            return {
                **asset_dict,
                "version": version,
            }
        else:
            return asset_dict["path"]
