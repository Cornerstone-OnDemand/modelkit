import os
from typing import Optional

import pydantic
from tenacity import retry

from modelkit.assets import errors
from modelkit.assets.drivers.retry import RETRY_POLICY
from modelkit.assets.log import logger

try:
    from google.api_core.exceptions import NotFound
    from google.cloud import storage
    from google.cloud.storage import Client
except ImportError:
    logger.debug(
        "GCS is not available "
        "(install modelkit[gcs] or google-cloud-storage directly)"
    )


class GCSDriverSettings(pydantic.BaseSettings):
    bucket: str = pydantic.Field(..., env="ASSETS_BUCKET_NAME")
    service_account_path: Optional[str] = None
    client: Optional[storage.Client]

    class Config:
        extra = "forbid"


class GCSStorageDriver:
    def __init__(self, settings: GCSDriverSettings = None):
        if not settings:
            settings = GCSDriverSettings()
        self.bucket = settings.bucket

        if settings.client:
            self.client = settings.client
        else:
            if settings.service_account_path:
                self.client = Client.from_service_account_json(
                    settings.service_account_path
                )
            else:
                self.client = Client()

    @retry(**RETRY_POLICY)
    def iterate_objects(self, prefix=None):
        bucket = self.client.bucket(self.bucket)
        for blob in bucket.list_blobs(prefix=prefix):
            yield blob.name

    @retry(**RETRY_POLICY)
    def upload_object(self, file_path, object_name):
        bucket = self.client.bucket(self.bucket)
        blob = bucket.blob(object_name)
        storage.blob._DEFAULT_CHUNKSIZE = 2097152  # 2 MB
        storage.blob._MAX_MULTIPART_SIZE = 2097152  # 2 MB
        with open(file_path, "rb") as f:
            blob.upload_from_file(f)

    @retry(**RETRY_POLICY)
    def download_object(self, object_name, destination_path):
        bucket = self.client.bucket(self.bucket)
        blob = bucket.blob(object_name)
        try:
            with open(destination_path, "wb") as f:
                blob.download_to_file(f)
        except NotFound:
            logger.error(
                "Object not found.", bucket=self.bucket, object_name=object_name
            )
            os.remove(destination_path)
            raise errors.ObjectDoesNotExistError(
                driver=self, bucket=self.bucket, object_name=object_name
            )

    @retry(**RETRY_POLICY)
    def delete_object(self, object_name):
        bucket = self.client.bucket(self.bucket)
        blob = bucket.blob(object_name)
        blob.delete()

    @retry(**RETRY_POLICY)
    def exists(self, object_name):
        bucket = self.client.bucket(self.bucket)
        blob = bucket.blob(object_name)
        return blob.exists()
