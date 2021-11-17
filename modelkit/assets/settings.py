import os
import re
import typing

from modelkit.assets import errors
from modelkit.assets.versioning.major_minor import MajorMinorAssetsVersioningSystem
from modelkit.assets.versioning.simple_date import SimpleDateAssetsVersioningSystem
from modelkit.assets.versioning.versioning import AssetsVersioningSystem

GENERIC_ASSET_NAME_RE = (
    r"(([A-Z]:\\)|/)?[a-zA-Z0-9]([a-zA-Z0-9\-\_\.\/\\]*[a-zA-Z0-9])?"
)
GENERIC_ASSET_VERSION_RE = r"(?P<version>[0-9A-Za-z\.\-\_]+?)"


REMOTE_ASSET_RE = (
    rf"^(?P<name>{GENERIC_ASSET_NAME_RE})"
    rf"(:{GENERIC_ASSET_VERSION_RE})?"
    rf"(\[(?P<sub_part>(\/?{GENERIC_ASSET_NAME_RE})+)\])?$"
)


class AssetSpec:
    versioning: AssetsVersioningSystem

    def __init__(
        self,
        name: str,
        versioning: str = None,
        version: str = None,
        sub_part: str = None,
    ) -> None:

        versioning = (
            versioning
            or os.environ.get("MODELKIT_ASSETS_VERSIONING_SYSTEM")
            or "major_minor"
        )

        if versioning == "major_minor":
            self.versioning = MajorMinorAssetsVersioningSystem()
        elif versioning == "simple_date":
            self.versioning = SimpleDateAssetsVersioningSystem()
        else:
            raise errors.UnknownAssetsVersioningSystemError(versioning)

        self.check_name_valid(name)
        self.name = name
        if version:
            self.check_version_valid(version)
            self.versioning.check_version_valid(version)

        self.version = version
        self.sub_part = sub_part

    def is_version_complete(self):
        if self.version:
            return self.versioning.is_version_complete(self.version)
        return False

    def sort_versions(self, version_list: typing.Iterable[str]) -> typing.List[str]:
        return self.versioning.sort_versions(version_list)

    def set_latest_version(self, all_versions: typing.List[str]):
        if not self.version:
            self.version = all_versions[0]
        else:
            self.version = self.versioning.get_latest_partial_version(
                self.version, all_versions
            )

    def get_local_versions(self, local_name) -> typing.List[str]:
        if os.path.isdir(local_name):
            return self.versioning.sort_versions(
                version_list=[
                    d
                    for d in os.listdir(local_name)
                    if self.versioning.is_version_valid(d)
                ]
            )
        else:
            return []

    @classmethod
    def check_name_valid(cls, name: str):
        if not re.fullmatch(GENERIC_ASSET_NAME_RE, name):
            raise errors.InvalidNameError(
                f"Invalid name `{name}`, can only contain [a-z], [0-9], [/], [-] or [_]"
            )

    @classmethod
    def check_version_valid(cls, name: str):
        if name and not re.fullmatch(GENERIC_ASSET_VERSION_RE, name):
            raise errors.InvalidVersionError(
                f"Invalid version `{name}`, can only contain [a-zA-Z0-9], [-._]"
            )

    @staticmethod
    def from_string(
        input_string: str,
        versioning: str = None,
    ):
        match = re.match(REMOTE_ASSET_RE, input_string)
        if not match:
            raise errors.InvalidAssetSpecError(input_string)

        return AssetSpec(versioning=versioning, **match.groupdict())

    def __eq__(self, other):
        if not isinstance(other, AssetSpec):
            return False

        return (
            self.name == other.name
            and self.version == other.version
            and self.sub_part == other.sub_part
        )
