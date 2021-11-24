import re
import typing

from modelkit.assets import errors
from modelkit.assets.versioning import versioning

MAJOR_MINOR_VERSION_RE = r"(?P<major>[0-9]+)(\.(?P<minor>[0-9]+))?"


class InvalidMajorVersionError(errors.InvalidVersionError):
    def __init__(self, version_str):
        super().__init__(f"Major version string `{version_str}` is not valid.")


class MajorVersionDoesNotExistError(errors.InvalidVersionError):
    def __init__(self, version_str):
        super().__init__(f"Major version `{version_str}` not present.")


class MajorMinorAssetsVersioningSystem(versioning.AssetsVersioningSystem):
    @classmethod
    def get_initial_version(cls) -> str:
        return "0.0"

    @classmethod
    def check_version_valid(cls, version: str):
        if version:
            major_version, minor_version = cls._parse_version_str(version)
            cls._check_version_number(major_version)
            cls._check_version_number(minor_version)
            cls._check_major_version(major_version, minor_version)

    @classmethod
    def is_version_complete(cls, version: str):
        try:
            major_version, minor_version = cls._parse_version_str(version)
        except InvalidMajorVersionError:
            return False
        return major_version is not None and minor_version is not None

    @classmethod
    def sort_versions(cls, version_list: typing.Iterable[str]) -> typing.List[str]:
        def _key(v):
            maj_v, min_v = cls._parse_version(v)
            if min_v is None:
                min_v = 0
            return maj_v, min_v

        return sorted(version_list, reverse=True, key=_key)

    @classmethod
    def get_update_cli_params(cls, **kwargs) -> typing.Dict[str, typing.Any]:
        current_major_version = None
        if kwargs["version"]:
            current_major_version, _ = cls._parse_version_str(kwargs["version"])
        major_versions = {cls._parse_version_str(v)[0] for v in kwargs["version_list"]}
        display = [
            f'Found a total of {len(kwargs["version_list"])} versions ',
            f"({len(major_versions)} major versions) ",
        ]
        for major_version in sorted(major_versions):
            display.append(
                f" - major `{major_version}` = "
                + ", ".join(
                    cls.filter_versions(
                        kwargs["version_list"], major=str(major_version)
                    )
                )
            )
        return {
            "display": "\n".join(display),
            "params": {
                "bump_major": kwargs["bump_major"],
                "major": current_major_version,
            },
        }

    @classmethod
    def get_latest_partial_version(
        cls, version: str, versions: typing.List[str]
    ) -> str:
        major_version, _ = cls._parse_version_str(version)
        if major_version:
            return cls.filter_versions(versions, major=major_version)[0]
        else:
            return versions[0]

    @staticmethod
    def _check_major_version(major_version, minor_version):
        if minor_version and not major_version:
            raise errors.InvalidVersionError(
                "Cannot specify a minor version without a major version."
            )

    @staticmethod
    def _check_version_number(minor_or_major):
        if minor_or_major and not re.fullmatch("^[0-9]+$", minor_or_major):
            raise errors.InvalidVersionError(
                f"Invalid version `{minor_or_major}` is not a number"
            )

    @staticmethod
    def _parse_version_str(version: str):
        m = re.fullmatch(MAJOR_MINOR_VERSION_RE, version)
        if not m:
            raise errors.InvalidVersionError(version)
        d = m.groupdict()
        return (d["major"], d["minor"] if d.get("minor") else None)

    @classmethod
    def _parse_version(cls, version_str):
        major, minor = cls._parse_version_str(version_str)
        return (int(major), int(minor) if minor is not None else None)

    @classmethod
    def increment_version(
        cls, version_list: typing.List[str] = None, params: typing.Dict[str, str] = None
    ) -> str:
        version_list = version_list or []
        params = params or {}

        if params["bump_major"]:
            version = cls.latest_version(version_list)
        else:
            version = cls.latest_version(version_list, major=params["major"])

        v_major, v_minor = cls._parse_version(version)

        if params["bump_major"]:
            v_major += 1
            v_minor = 0
        else:
            v_minor += 1

        return f"{v_major}.{v_minor}"

    @staticmethod
    def filter_versions(version_list, major):
        if not re.fullmatch("[0-9]+", major):
            raise InvalidMajorVersionError(major)
        return [v for v in version_list if re.match(f"^{major}" + r".", v)]

    @classmethod
    def latest_version(cls, version_list, major=None):
        if major:
            filtered_version_list = list(cls.filter_versions(version_list, major))
            if not filtered_version_list:
                raise MajorVersionDoesNotExistError(major)
            return cls.sort_versions(filtered_version_list)[0]
        return cls.sort_versions(version_list)[0]
