import datetime
import re
import typing

from modelkit.assets import errors
from modelkit.assets.versioning import versioning

DATE_RE = r"^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z$"


class SimpleDateAssetsVersioningSystem(versioning.AssetsVersioningSystem):
    @classmethod
    def get_initial_version(cls) -> str:
        return _utcnow()

    @classmethod
    def check_version_valid(cls, version: str):
        if not re.fullmatch(DATE_RE, version):
            raise errors.InvalidVersionError(f"Invalid version `{version}`")

    @classmethod
    def sort_versions(cls, version_list: typing.Iterable[str]) -> typing.List[str]:
        return sorted(version_list, reverse=True)

    @classmethod
    def get_update_cli_params(cls, **kwargs) -> typing.Dict[str, typing.Any]:
        display: typing.List[str] = []
        display.append(f'Found a total of {len(kwargs["version_list"])} versions ')
        display.append(f'{kwargs["version_list"]}')
        display.append(f'Last version is {kwargs["version_list"][0]}')

        return {
            "display": "\n".join(display),
            "params": {},
        }

    @classmethod
    def increment_version(
        cls, version_list: typing.List[str] = None, params: typing.Dict[str, str] = None
    ) -> str:
        return _utcnow()


def _utcnow() -> str:
    """string iso format in UTC"""
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
