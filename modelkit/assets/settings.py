import re
from typing import Optional

from pydantic import BaseModel, validator
from structlog import get_logger

from modelkit.assets.errors import InvalidAssetSpecError

SUPPORTED_MODELKIT_STORAGE_PROVIDERS = {"s3", "gcs", "local"}

logger = get_logger(__name__)

NAME_RE = r"[a-z0-9]([a-z0-9\-\_\.]*[a-z0-9])?"

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
