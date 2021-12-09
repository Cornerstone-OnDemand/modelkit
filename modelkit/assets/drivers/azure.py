import os
from typing import Optional

from azure.storage.blob import BlobServiceClient
from structlog import get_logger
from tenacity import retry

from modelkit.assets import errors
from modelkit.assets.drivers.abc import StorageDriver
from modelkit.assets.drivers.retry import RETRY_POLICY

logger = get_logger(__name__)


class AzureStorageDriver(StorageDriver):
    bucket: str

    def __init__(
        self,
        bucket: Optional[str] = None,
        connection_string: Optional[str] = None,
        client: Optional[BlobServiceClient] = None,
    ):
        self.bucket = bucket or os.environ.get("MODELKIT_STORAGE_BUCKET") or ""
        if not self.bucket:
            raise ValueError("Bucket needs to be set for Azure storage driver")

        if client:
            self.client = client
        elif connection_string:  # pragma: no cover
            self.client = BlobServiceClient.from_connection_string(connection_string)
        else:
            self.client = BlobServiceClient.from_connection_string(
                os.environ["AZURE_STORAGE_CONNECTION_STRING"]
            )

    @retry(**RETRY_POLICY)
    def iterate_objects(self, prefix=None):
        container = self.client.get_container_client(self.bucket)
        for blob in container.list_blobs(prefix=prefix):
            yield blob["name"]

    @retry(**RETRY_POLICY)
    def upload_object(self, file_path, object_name):
        blob_client = self.client.get_blob_client(
            container=self.bucket, blob=object_name
        )
        if blob_client.exists():
            self.delete_object(object_name)
        with open(file_path, "rb") as f:
            blob_client.upload_blob(f)

    @retry(**RETRY_POLICY)
    def download_object(self, object_name, destination_path):
        blob_client = self.client.get_blob_client(
            container=self.bucket, blob=object_name
        )
        if not blob_client.exists():
            logger.error(
                "Object not found.", bucket=self.bucket, object_name=object_name
            )
            if os.path.exists(destination_path):
                os.remove(destination_path)
            raise errors.ObjectDoesNotExistError(
                driver=self, bucket=self.bucket, object_name=object_name
            )
        with open(destination_path, "wb") as f:
            f.write(blob_client.download_blob().readall())

    @retry(**RETRY_POLICY)
    def delete_object(self, object_name):
        blob_client = self.client.get_blob_client(
            container=self.bucket, blob=object_name
        )
        blob_client.delete_blob()

    @retry(**RETRY_POLICY)
    def exists(self, object_name):
        blob_client = self.client.get_blob_client(
            container=self.bucket, blob=object_name
        )
        return blob_client.exists()

    def get_object_uri(self, object_name, sub_part=None):
        return "azfs://" + "/".join(
            (self.bucket, object_name, *(sub_part or "").split("/"))
        )
