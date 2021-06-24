import os

import boto3
import botocore
import pydantic
from pydantic import BaseSettings
from structlog import get_logger
from tenacity import retry

from modelkit.assets import errors
from modelkit.assets.drivers.retry import RETRY_POLICY

logger = get_logger(__name__)


class S3DriverSettings(BaseSettings):
    bucket: str = pydantic.Field(..., env="MODELKIT_STORAGE_BUCKET")
    aws_access_key_id: str = pydantic.Field(None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = pydantic.Field(None, env="AWS_SECRET_ACCESS_KEY")
    aws_default_region: str = pydantic.Field(None, env="AWS_DEFAULT_REGION")
    aws_session_token: str = pydantic.Field(None, env="AWS_SESSION_TOKEN")
    s3_endpoint: str = pydantic.Field(None, env="S3_ENDPOINT")

    class Config:
        extra = "forbid"


class S3StorageDriver:
    def __init__(self, settings: S3DriverSettings = None):
        if not settings:
            settings = S3DriverSettings()
        self.bucket = settings.bucket
        self.endpoint_url = settings.s3_endpoint
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            aws_session_token=settings.aws_session_token,
            region_name=settings.aws_default_region,
        )
        self.bucket = settings.bucket

    @retry(**RETRY_POLICY)
    def iterate_objects(self, prefix=None):
        paginator = self.client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=self.bucket, Prefix=prefix or "")
        for page in pages:
            for obj in page.get("Contents", []):
                yield obj["Key"]

    @retry(**RETRY_POLICY)
    def upload_object(self, file_path, object_name):
        self.client.upload_file(file_path, self.bucket, object_name)

    @retry(**RETRY_POLICY)
    def download_object(self, object_name, destination_path):
        try:
            with open(destination_path, "wb") as f:
                self.client.download_fileobj(self.bucket, object_name, f)
        except botocore.exceptions.ClientError:
            logger.error(
                "Object not found.", bucket=self.bucket, object_name=object_name
            )
            os.remove(destination_path)
            raise errors.ObjectDoesNotExistError(
                driver=self, bucket=self.bucket, object_name=object_name
            )

    @retry(**RETRY_POLICY)
    def delete_object(self, object_name):
        self.client.delete_object(Bucket=self.bucket, Key=object_name)

    @retry(**RETRY_POLICY)
    def exists(self, object_name):
        try:
            self.client.head_object(Bucket=self.bucket, Key=object_name)
            return True
        except botocore.exceptions.ClientError:
            return False

    def __repr__(self):
        return f"<S3StorageDriver endpoint_url={self.endpoint_url}>"
