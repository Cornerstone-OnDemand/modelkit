import os
from typing import Dict, Optional, Union

import pydantic
from azure.storage.blob import BlobServiceClient
from structlog import get_logger
from tenacity import retry

from modelkit.assets import errors
from modelkit.assets.drivers.abc import StorageDriver, StorageDriverSettings
from modelkit.assets.drivers.retry import retry_policy

logger = get_logger(__name__)

AZURE_RETRY_POLICY = retry_policy()


class AzureStorageDriverSettings(StorageDriverSettings):
    connection_string: Optional[str] = pydantic.Field(
        None,
        validation_alias=pydantic.AliasChoices(
            "connection_string", "AZURE_STORAGE_CONNECTION_STRING"
        ),
    )
    model_config = pydantic.ConfigDict(extra="forbid")


class AzureStorageDriver(StorageDriver):
    def __init__(
        self,
        settings: Union[Dict, AzureStorageDriverSettings],
        client: Optional[BlobServiceClient] = None,
    ):
        if isinstance(settings, dict):
            settings = AzureStorageDriverSettings(**settings)
        if not (client or settings.connection_string):
            raise ValueError(
                "Connection string needs to be set for Azure storage driver"
            )
        super().__init__(
            settings,
            client,
            client_configuration={"connection_string": settings.connection_string},
        )

    @staticmethod
    def build_client(client_configuration: Dict[str, str]) -> BlobServiceClient:
        connection_string = client_configuration.get("connection_string")
        if not connection_string:
            raise ValueError(
                "Connection string needs to be set for Azure storage driver"
            )
        return BlobServiceClient.from_connection_string(connection_string)

    @retry(**AZURE_RETRY_POLICY)
    def iterate_objects(self, prefix=None):
        container = self.client.get_container_client(self.bucket)
        for blob in container.list_blobs(prefix=prefix):
            yield blob["name"]

    @retry(**AZURE_RETRY_POLICY)
    def upload_object(self, file_path, object_name):
        blob_client = self.client.get_blob_client(
            container=self.bucket, blob=object_name
        )
        if blob_client.exists():
            self.delete_object(object_name)
        with open(file_path, "rb") as f:
            blob_client.upload_blob(f)

    @retry(**AZURE_RETRY_POLICY)
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

    @retry(**AZURE_RETRY_POLICY)
    def delete_object(self, object_name):
        blob_client = self.client.get_blob_client(
            container=self.bucket, blob=object_name
        )
        blob_client.delete_blob()

    @retry(**AZURE_RETRY_POLICY)
    def exists(self, object_name):
        blob_client = self.client.get_blob_client(
            container=self.bucket, blob=object_name
        )
        return blob_client.exists()

    def get_object_uri(self, object_name, sub_part=None):
        return "azfs://" + "/".join(
            (self.bucket, object_name, *(sub_part or "").split("/"))
        )
