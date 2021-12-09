import os
from typing import Optional

from google.api_core.exceptions import NotFound
from google.cloud import storage
from google.cloud.storage import Client
from structlog import get_logger
from tenacity import retry

from modelkit.assets import errors
from modelkit.assets.drivers.abc import StorageDriver
from modelkit.assets.drivers.retry import RETRY_POLICY

logger = get_logger(__name__)


class GCSStorageDriver(StorageDriver):
    bucket: str
    client: Client

    def __init__(
        self,
        bucket: Optional[str] = None,
        service_account_path: Optional[str] = None,
        client: Optional[Client] = None,
    ):
        self.bucket = bucket or os.environ.get("MODELKIT_STORAGE_BUCKET") or ""
        if not self.bucket:
            raise ValueError("Bucket needs to be set for GCS storage driver")

        if client:
            self.client = client
        elif service_account_path:  # pragma: no cover
            self.client = Client.from_service_account_json(service_account_path)
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

    def get_object_uri(self, object_name, sub_part=None):
        return "gs://" + "/".join(
            (self.bucket, object_name, *(sub_part or "").split("/"))
        )
