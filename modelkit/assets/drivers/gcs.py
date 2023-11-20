import os
from typing import Dict, Optional, Union

import pydantic
from google.api_core.exceptions import GoogleAPIError, NotFound
from google.cloud import storage
from google.cloud.storage import Client
from structlog import get_logger
from tenacity import retry

from modelkit.assets import errors
from modelkit.assets.drivers.abc import StorageDriver, StorageDriverSettings
from modelkit.assets.drivers.retry import retry_policy

logger = get_logger(__name__)

GCS_RETRY_POLICY = retry_policy(GoogleAPIError)


class GCSStorageDriverSettings(StorageDriverSettings):
    service_account_path: Optional[str] = pydantic.Field(
        None,
        validation_alias=pydantic.AliasChoices(
            "service_account_path", "GOOGLE_APPLICATION_CREDENTIALS"
        ),
    )
    model_config = pydantic.ConfigDict(extra="forbid")


class GCSStorageDriver(StorageDriver):
    def __init__(
        self,
        settings: Union[Dict, GCSStorageDriverSettings],
        client: Optional[Client] = None,
    ):
        if isinstance(settings, dict):
            settings = GCSStorageDriverSettings(**settings)

        super().__init__(
            settings=settings,
            client=client,
            client_configuration={
                "service_account_path": settings.service_account_path
            },
        )

    @staticmethod
    def build_client(client_configuration: Dict[str, str]) -> Client:
        sa_path = client_configuration.get("service_account_path")
        if sa_path:
            return Client.from_service_account_json(sa_path)
        return Client()

    @retry(**GCS_RETRY_POLICY)
    def iterate_objects(self, prefix=None):
        bucket = self.client.bucket(self.bucket)
        for blob in bucket.list_blobs(prefix=prefix):
            yield blob.name

    @retry(**GCS_RETRY_POLICY)
    def upload_object(self, file_path, object_name):
        bucket = self.client.bucket(self.bucket)
        blob = bucket.blob(object_name)
        storage.blob._DEFAULT_CHUNKSIZE = 2097152  # 2 MB
        storage.blob._MAX_MULTIPART_SIZE = 2097152  # 2 MB
        with open(file_path, "rb") as f:
            blob.upload_from_file(f)

    @retry(**GCS_RETRY_POLICY)
    def download_object(self, object_name, destination_path):
        bucket = self.client.bucket(self.bucket)
        blob = bucket.blob(object_name)
        try:
            with open(destination_path, "wb") as f:
                blob.download_to_file(f)
        except NotFound as e:
            logger.error(
                "Object not found.", bucket=self.bucket, object_name=object_name
            )
            os.remove(destination_path)
            raise errors.ObjectDoesNotExistError(
                driver=self, bucket=self.bucket, object_name=object_name
            ) from e

    @retry(**GCS_RETRY_POLICY)
    def delete_object(self, object_name):
        bucket = self.client.bucket(self.bucket)
        blob = bucket.blob(object_name)
        blob.delete()

    @retry(**GCS_RETRY_POLICY)
    def exists(self, object_name):
        bucket = self.client.bucket(self.bucket)
        blob = bucket.blob(object_name)
        return blob.exists()

    def get_object_uri(self, object_name, sub_part=None):
        return "gs://" + "/".join(
            (self.bucket, object_name, *(sub_part or "").split("/"))
        )
