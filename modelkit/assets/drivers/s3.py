import os
from typing import Dict, Optional, Union

import boto3
import botocore
import pydantic
from structlog import get_logger
from tenacity import retry

from modelkit.assets import errors
from modelkit.assets.drivers.abc import StorageDriver, StorageDriverSettings
from modelkit.assets.drivers.retry import retry_policy

logger = get_logger(__name__)

S3_RETRY_POLICY = retry_policy(botocore.exceptions.ClientError)


class S3StorageDriverSettings(StorageDriverSettings):
    aws_access_key_id: Optional[str] = pydantic.Field(
        None,
        validation_alias=pydantic.AliasChoices(
            "aws_access_key_id", "AWS_ACCESS_KEY_ID"
        ),
    )
    aws_secret_access_key: Optional[str] = pydantic.Field(
        None,
        validation_alias=pydantic.AliasChoices(
            "aws_secret_access_key", "AWS_SECRET_ACCESS_KEY"
        ),
    )
    aws_default_region: Optional[str] = pydantic.Field(
        None,
        validation_alias=pydantic.AliasChoices(
            "aws_default_region", "AWS_DEFAULT_REGION"
        ),
    )
    aws_session_token: Optional[str] = pydantic.Field(
        None,
        validation_alias=pydantic.AliasChoices(
            "aws_session_token", "AWS_SESSION_TOKEN"
        ),
    )
    s3_endpoint: Optional[str] = pydantic.Field(
        None, validation_alias=pydantic.AliasChoices("s3_endpoint", "S3_ENDPOINT")
    )
    aws_kms_key_id: Optional[str] = pydantic.Field(
        None, validation_alias=pydantic.AliasChoices("aws_kms_key_id", "AWS_KMS_KEY_ID")
    )
    model_config = pydantic.ConfigDict(extra="forbid")


class S3StorageDriver(StorageDriver):
    def __init__(
        self,
        settings: Union[Dict, S3StorageDriverSettings],
        client: Optional[boto3.client] = None,
    ):
        if isinstance(settings, dict):
            settings = S3StorageDriverSettings(**settings)

        client_configuration = {
            "endpoint_url": settings.s3_endpoint,
            "aws_access_key_id": settings.aws_access_key_id,
            "aws_secret_access_key": settings.aws_secret_access_key,
            "region_name": settings.aws_default_region,
            "aws_session_token": settings.aws_session_token,
        }
        self.aws_kms_key_id = settings.aws_kms_key_id
        super().__init__(
            settings=settings, client=client, client_configuration=client_configuration
        )

    @staticmethod
    def build_client(client_configuration: Dict[str, str]) -> boto3.client:
        return boto3.client("s3", **client_configuration)

    @retry(**S3_RETRY_POLICY)
    def iterate_objects(self, prefix=None):
        paginator = self.client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=self.bucket, Prefix=prefix or "")
        for page in pages:
            for obj in page.get("Contents", []):
                yield obj["Key"]

    @retry(**S3_RETRY_POLICY)
    def upload_object(self, file_path, object_name):
        if self.aws_kms_key_id:
            self.client.upload_file(  # pragma: no cover
                file_path,
                self.bucket,
                object_name,
                ExtraArgs={
                    "ServerSideEncryption": "aws:kms",
                    "SSEKMSKeyId": self.aws_kms_key_id,
                },
            )
        else:
            self.client.upload_file(file_path, self.bucket, object_name)

    @retry(**S3_RETRY_POLICY)
    def download_object(self, object_name, destination_path):
        try:
            with open(destination_path, "wb") as f:
                self.client.download_fileobj(self.bucket, object_name, f)
        except botocore.exceptions.ClientError as e:
            logger.error(
                "Object not found.", bucket=self.bucket, object_name=object_name
            )
            os.remove(destination_path)
            raise errors.ObjectDoesNotExistError(
                driver=self, bucket=self.bucket, object_name=object_name
            ) from e

    @retry(**S3_RETRY_POLICY)
    def delete_object(self, object_name):
        self.client.delete_object(Bucket=self.bucket, Key=object_name)

    @retry(**S3_RETRY_POLICY)
    def exists(self, object_name):
        try:
            self.client.head_object(Bucket=self.bucket, Key=object_name)
            return True
        except botocore.exceptions.ClientError:
            return False

    def __repr__(self):
        return "<S3StorageDriver endpoint_url={}>".format(
            self.client_configuration["endpoint_url"]
        )

    def get_object_uri(self, object_name, sub_part=None):
        return "s3://" + "/".join(
            (self.bucket, object_name, *(sub_part or "").split("/"))
        )
