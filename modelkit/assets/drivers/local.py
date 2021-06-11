import glob
import os
import shutil

import pydantic
from pydantic import BaseSettings
from structlog import get_logger

from modelkit.assets import errors

logger = get_logger(__name__)


class LocalDriverSettings(BaseSettings):
    bucket: pydantic.DirectoryPath = pydantic.Field(..., env="MODELKIT_STORAGE_BUCKET")

    class Config:
        extra = "forbid"


class LocalStorageDriver:
    def __init__(self, settings: LocalDriverSettings = None):
        if not settings:
            settings = LocalDriverSettings()
        self.bucket = settings.bucket

    def iterate_objects(self, prefix=None):
        if not os.path.isdir(self.bucket):
            raise errors.ContainerDoesNotExistError(self, self.bucket)
        for filename in glob.iglob(
            os.path.join(self.bucket, os.path.join("**", "*")), recursive=True
        ):
            if os.path.isfile(filename):
                yield "/".join(os.path.split(os.path.relpath(filename, self.bucket)))

    def upload_object(self, file_path, object_name):
        object_path = os.path.join(self.bucket, *object_name.split("/"))
        object_dir, _ = os.path.split(object_path)

        # delete whatever is locally at the position of the object
        if os.path.isfile(object_path):
            os.remove(object_path)
        if os.path.isdir(object_path):
            shutil.rmtree(object_path)
        if os.path.isfile(object_dir):
            os.remove(object_dir)
        os.makedirs(object_dir, exist_ok=True)

        with open(file_path, "rb") as fsrc:
            with open(object_path, "xb") as fdst:
                shutil.copyfileobj(fsrc, fdst)

    def download_object(self, object_name, destination_path):
        object_path = os.path.join(self.bucket, *object_name.split("/"))
        if not os.path.isfile(object_path):
            logger.error(
                "Object not found.", bucket=self.bucket, object_name=object_name
            )
            raise errors.ObjectDoesNotExistError(
                driver=self, bucket=self.bucket, object_name=object_name
            )

        with open(object_path, "rb") as fsrc:
            with open(destination_path, "wb") as fdst:
                shutil.copyfileobj(fsrc, fdst)

    def delete_object(self, object_name):
        object_path = os.path.join(self.bucket, *object_name.split("/"))
        if os.path.exists(object_path):
            os.remove(object_path)

    def exists(self, object_name):
        return os.path.isfile(os.path.join(self.bucket, *object_name.split("/")))

    def __repr__(self):
        return f"<LocalStorageDriver bucket={self.bucket}>"
