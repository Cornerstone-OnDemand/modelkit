import os
from typing import Optional

import pydantic
from google.api_core.exceptions import NotFound
from google.cloud import storage
from google.cloud.storage import Client
from tenacity import retry

from modelkit.assets import errors
from modelkit.assets.drivers.retry import RETRY_POLICY
from modelkit.assets.log import logger


class GCSDriverSettings(pydantic.BaseSettings):
    bucket: str = pydantic.Field(..., env="ASSETS_BUCKET_NAME")
    service_account_path: Optional[str] = None

    class Config:
        extra = "forbid"


class GCSStorageDriver:
    def __init__(self, settings: GCSDriverSettings = None, client=None):
        if not settings:
            settings = GCSDriverSettings()
        self.bucket = settings.bucket

        if client:
            self.client = client
        else:
            if settings.service_account_path:
                self.client = Client.from_service_account_json(
                    settings.service_account_path
                )
            else:
                self.client = Client()

    @retry(**RETRY_POLICY)
    def iterate_objects(self, bucket, prefix=None):
        bucket = self.client.bucket(bucket)
        for blob in bucket.list_blobs(prefix=prefix):
            yield blob.name

    @retry(**RETRY_POLICY)
    def upload_object(self, file_path, bucket, object_name):
        bucket = self.client.bucket(bucket)
        blob = bucket.blob(object_name)
        storage.blob._DEFAULT_CHUNKSIZE = 2097152  # 2 MB
        storage.blob._MAX_MULTIPART_SIZE = 2097152  # 2 MB
        with open(file_path, "rb") as f:
            blob.upload_from_file(f)

    @retry(**RETRY_POLICY)
    def download_object(self, bucket_name, object_name, destination_path):
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        try:
            with open(destination_path, "wb") as f:
                blob.download_to_file(f)
        except NotFound:
            logger.error(
                "Object not found.", bucket=bucket_name, object_name=object_name
            )
            os.remove(destination_path)
            raise errors.ObjectDoesNotExistError(
                driver=self, bucket=bucket_name, object_name=object_name
            )

    @retry(**RETRY_POLICY)
    def delete_object(self, bucket, object_name):
        bucket = self.client.bucket(bucket)
        blob = bucket.blob(object_name)
        blob.delete()

    @retry(**RETRY_POLICY)
    def exists(self, bucket, object_name):
        bucket = self.client.bucket(bucket)
        blob = bucket.blob(object_name)
        return blob.exists()
