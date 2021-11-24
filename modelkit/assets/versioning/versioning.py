import abc
import typing

from modelkit.assets import errors


class AssetsVersioningSystem(abc.ABC):
    @abc.abstractclassmethod
    def get_initial_version(cls) -> str:  # pragma: no cover
        """return an initial version"""
        ...

    @abc.abstractclassmethod
    def check_version_valid(cls, version: str):  # pragma: no cover
        """raises InvalidVersionError if version is not valid"""
        ...

    @abc.abstractclassmethod
    def sort_versions(
        cls, version_list: typing.Iterable[str]
    ) -> typing.List[str]:  # pragma: no cover
        """Sort the version_list according to the versioning system"""
        ...

    @abc.abstractclassmethod
    def increment_version(
        cls, version_list: typing.List[str] = None, params: typing.Dict[str, str] = None
    ) -> str:  #  pragma: no cover
        """Algorithm used to increment your version. Returns new version"""
        ...

    @abc.abstractclassmethod
    def get_update_cli_params(cls, **kwargs) -> typing.Dict[str, typing.Any]:
        """
            returns {
                "display":
                "params" :
            }
        where:
            - display is the versioning system specific text that will be display in the
            update cli
            - params are the params that will be forward to increment_version method

        """
        ...

    @classmethod
    def is_version_complete(cls, version: str) -> bool:  # pragma: no cover
        """Override for a system with partial / incomplete version"""
        return True

    @classmethod
    def get_latest_partial_version(
        cls, version: str, versions: typing.List[str]
    ) -> str:  # pragma: no cover
        """Override for a system with partial / incomplete version"""
        return versions[0]

    def is_version_valid(self, version: str) -> bool:
        try:
            self.check_version_valid(version)
            return True
        except errors.InvalidVersionError:
            return False
