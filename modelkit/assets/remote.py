import datetime
import glob
import json
import os
import tempfile
import time

import humanize
from dateutil import parser, tz
from structlog import get_logger

from modelkit.assets import errors
from modelkit.assets.drivers import settings_to_driver
from modelkit.assets.settings import RemoteAssetsStoreSettings
from modelkit.assets.versioning import (
    MajorVersionDoesNotExistError,
    increment_version,
    sort_versions,
)
from modelkit.utils.logging import ContextualizedLogging

logger = get_logger(__name__)


def get_size(dir_path):
    if os.path.isfile(dir_path):
        return os.stat(dir_path).st_size
    return sum(
        os.stat(f).st_size
        for f in glob.iglob(os.path.join(dir_path, "**/*"), recursive=True)
        if os.path.isfile(f)
    )


class RemoteAssetsStore:
    def __init__(self, **settings):
        settings = RemoteAssetsStoreSettings(**settings)

        self.driver = settings_to_driver(settings.driver)
        if self.driver:
            self.bucket = self.driver.bucket
            self.timeout = settings.timeout_s
            self.prefix = settings.storage_prefix
            self.force_download = settings.storage_force_download

    def get_object_name(self, name, version):
        return "/".join((self.prefix, name, version))

    def get_meta_object_name(self, name, version):
        return self.get_object_name(name, version) + ".meta"

    def get_versions_object_name(self, name):
        return "/".join((self.prefix, name + ".versions"))

    def get_versions_info(self, name):
        """
        Retrieve asset versions information
        """
        versions_object_name = self.get_versions_object_name(name)
        with tempfile.TemporaryDirectory() as tmp_dir:
            versions_object_path = os.path.join(tmp_dir, name + ".version")
            os.makedirs(os.path.dirname(versions_object_path), exist_ok=True)
            self.driver.download_object(versions_object_name, versions_object_path)
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
            self.driver.download_object(meta_object_name, fdst)
            with open(fdst) as f:
                meta = json.load(f)
            meta["push_date"] = parser.isoparse(meta["push_date"])
        return meta

    def new(self, asset_path, name, dry_run=False):
        """
        Upload a new asset
        """
        versions_object_name = self.get_versions_object_name(name)
        if self.driver.exists(versions_object_name):
            raise errors.AssetAlreadyExistsError(name)
        logger.info(
            "Pushing new asset",
            name=name,
            asset_path=asset_path,
        )
        self.push(asset_path, name, "0.0", dry_run=dry_run)

        with tempfile.TemporaryDirectory() as dversions:
            with open(os.path.join(dversions, "versions.json"), "w") as f:
                json.dump({"versions": ["0.0"]}, f)
            logger.debug(
                "Pushing versions file",
                bucket=self.bucket,
                name=name,
            )
            if not dry_run:
                self.driver.upload_object(
                    os.path.join(dversions, "versions.json"),
                    versions_object_name,
                )

    def update(self, asset_path, name, bump_major=False, major=None, dry_run=False):
        """
        Update an existing asset version
        """
        versions_object_name = self.get_versions_object_name(name)
        if not self.driver.exists(versions_object_name):
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

        self.push(asset_path, name, new_version, dry_run=dry_run)

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
                self.driver.upload_object(versions_fn, versions_object_name)

    def push(self, asset_path, name, version, dry_run=False):
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
            if self.driver.exists(object_name):
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
                        self.driver.upload_object(path_to_push, remote_object_name)
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
                    self.driver.upload_object(asset_path, object_name)

            with tempfile.TemporaryDirectory() as tmp_dir:
                meta_file_path = os.path.join(tmp_dir, "asset.meta")
                with open(meta_file_path, "w", encoding="utf-8") as fmeta:
                    json.dump(meta, fmeta)

                logger.debug(
                    "Pushing meta file",
                    meta=meta,
                    bucket=self.bucket,
                    meta_object_name=object_name + ".meta",
                )
                if not dry_run:
                    self.driver.upload_object(meta_file_path, object_name + ".meta")

    def download(self, name, version, destination):
        """
        Retrieves the asset and returns a dictionary with meta information, asset
        origin (from cache) and local path
        """
        with ContextualizedLogging(name=name, version=version):
            destination_path = os.path.join(destination, *name.split("/"), version)
            object_name = self.get_object_name(name, version)
            meta = self.get_asset_meta(name, version)

            if meta.get("is_directory"):
                logger.info(
                    "Downloading remote multi-part asset",
                    n_parts=len(meta["contents"]),
                )
                t0 = time.monotonic()
                for part_no, part in enumerate(meta["contents"]):
                    current_destination_path = os.path.join(
                        destination_path, *part.split("/")
                    )
                    os.makedirs(
                        os.path.dirname(current_destination_path), exist_ok=True
                    )
                    remote_part_name = "/".join(
                        x for x in object_name.split("/") + part.split("/") if x
                    )
                    logger.debug(
                        "Downloading asset part",
                        part_no=part_no,
                        n_parts=len(meta["contents"]),
                    )
                    self.driver.download_object(
                        remote_part_name, current_destination_path
                    )
                    size = get_size(current_destination_path)
                    logger.debug(
                        "Downloaded asset part",
                        part_no=part_no,
                        n_parts=len(meta["contents"]),
                        size=humanize.naturalsize(size),
                        size_bytes=size,
                    )
                size = get_size(destination_path)
                logger.info(
                    "Downloaded remote multi-part asset",
                    size=humanize.naturalsize(size),
                    size_bytes=size,
                )
            else:
                logger.info("Downloading remote asset")
                t0 = time.monotonic()
                os.makedirs(os.path.dirname(destination_path), exist_ok=True)
                self.driver.download_object(object_name, destination_path)
                size = get_size(destination_path)
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
            # return
            return {"path": destination_path, "meta": meta}

    def iterate_assets(self):
        assets_set = set()
        for asset_path in self.driver.iterate_objects(self.prefix):
            if asset_path.endswith(".versions"):
                asset_name = "/".join(
                    asset_path[len(self.prefix) + 1 : -len(".versions")].split("/")
                )
                assets_set.add(asset_name)
        for asset_name in sorted(assets_set):
            versions_list = self.get_versions_info(asset_name)
            yield (asset_name, versions_list)
