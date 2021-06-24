import os
import re
from typing import Optional, Union

import pydantic
from pydantic import BaseModel, BaseSettings, ValidationError, root_validator, validator
from structlog import get_logger

from modelkit.assets.drivers.gcs import GCSDriverSettings
from modelkit.assets.drivers.local import LocalDriverSettings
from modelkit.assets.drivers.s3 import S3DriverSettings
from modelkit.assets.errors import InvalidAssetSpecError

SUPPORTED_MODELKIT_STORAGE_PROVIDERS = {"s3", "gcs", "local"}

logger = get_logger(__name__)


class DriverSettings(BaseSettings):
    storage_provider: str = pydantic.Field(None, env="MODELKIT_STORAGE_PROVIDER")
    settings: Optional[Union[GCSDriverSettings, S3DriverSettings, LocalDriverSettings]]

    @root_validator(pre=True)
    @classmethod
    def dispatch_settings(cls, fields):
        if "settings" in fields:
            return fields
        storage_provider = fields.pop("storage_provider", None)
        if storage_provider not in SUPPORTED_MODELKIT_STORAGE_PROVIDERS:
            logger.error(
                f"Unknown storage provider `{storage_provider}`, "
                "no remote storage will be available"
            )
            raise ValueError
        if storage_provider == "gcs":
            settings = GCSDriverSettings(**fields)
        if storage_provider == "s3":
            settings = S3DriverSettings(**fields)
        if storage_provider == "local":
            settings = LocalDriverSettings(**fields)
        return {"storage_provider": storage_provider, "settings": settings}


class RemoteAssetsStoreSettings(BaseSettings):
    driver: DriverSettings
    timeout_s: float = pydantic.Field(5 * 60, env="MODELKIT_STORAGE_TIMEOUT_S")
    storage_prefix: str = pydantic.Field(
        "modelkit-assets", env="MODELKIT_STORAGE_PREFIX"
    )
    storage_force_download: bool = pydantic.Field(
        False, env="MODELKIT_STORAGE_FORCE_DOWNLOAD"
    )

    @root_validator(pre=True)
    @classmethod
    def dispatch_settings(cls, fields):
        if "driver" not in fields:
            try:
                fields["driver"] = DriverSettings()
            except ValidationError:
                pass

        return fields

    @validator("storage_force_download", pre=True)
    def force_download(cls, v):
        return v == "True" or v is True


NAME_RE = r"[a-z0-9]([a-z0-9\-\_\.]*[a-z0-9])?"


class AssetsManagerSettings(BaseSettings):
    remote_store: Optional[RemoteAssetsStoreSettings]
    assets_dir: pydantic.DirectoryPath = pydantic.Field(
        default_factory=lambda: os.getcwd(), env="MODELKIT_ASSETS_DIR"
    )
    timeout: int = pydantic.Field(10, env="MODELKIT_ASSETS_TIMEOUT_S")

    @root_validator(pre=True)
    @classmethod
    def dispatch_settings(cls, fields):
        if "remote_store" not in fields:
            try:
                fields["remote_store"] = RemoteAssetsStoreSettings()
            except ValidationError:
                pass

        return fields

    class Config:
        env_prefix = ""
        case_sensitive = True
        extra = "forbid"


VERSION_SPEC_RE = r"(?P<major_version>[0-9]+)(\.(?P<minor_version>[0-9]+))?"

ASSET_NAME_RE = r"(([A-Z]:\\)|/)?[a-zA-Z0-9]([a-zA-Z0-9\-\_\.\/\\]*[a-zA-Z0-9])?"

REMOTE_ASSET_RE = (
    f"^(?P<name>{ASSET_NAME_RE})"
    rf"(:{VERSION_SPEC_RE})?(\[(?P<sub_part>(\/?{ASSET_NAME_RE})+)\])?$"
)


class AssetSpec(BaseModel):
    name: str
    major_version: Optional[str]
    minor_version: Optional[str]
    sub_part: Optional[str]

    @validator("name")
    @classmethod
    def is_name_valid(cls, v):
        if not re.fullmatch(ASSET_NAME_RE, v or ""):
            raise ValueError(
                f"Invalid name `{v}`, can only contain [a-z], [0-9], [/], [-] or [_]"
            )
        return v

    @validator("major_version")
    @classmethod
    def is_version_valid(cls, v):
        if v:
            if not re.fullmatch("^[0-9]+$", v):
                raise ValueError(f"Invalid asset version `{v}`")
        return v

    @validator("minor_version")
    @classmethod
    def has_major_version(cls, v, values):
        if v:
            if not values.get("major_version"):
                raise ValueError(
                    "Cannot specify a minor version without a major version."
                )
        return v

    @staticmethod
    def from_string(s):
        m = re.match(REMOTE_ASSET_RE, s)
        if not m:
            raise InvalidAssetSpecError(s)
        return AssetSpec(**m.groupdict())

    class Config:
        extra = "forbid"
