import abc
from typing import Any, Dict, Iterator, Optional, Union

import pydantic

from modelkit.core.settings import ModelkitSettings


class StorageDriverSettings(ModelkitSettings):
    bucket: str = pydantic.Field(
        ..., validation_alias=pydantic.AliasChoices("bucket", "MODELKIT_STORAGE_BUCKET")
    )
    lazy_driver: bool = pydantic.Field(
        False,
        validation_alias=pydantic.AliasChoices("lazy_driver", "MODELKIT_LAZY_DRIVER"),
    )
    model_config = pydantic.ConfigDict(extra="allow")


class StorageDriver(abc.ABC):
    def __init__(
        self,
        settings: Union[Dict, StorageDriverSettings],
        client: Optional[Any] = None,
        client_configuration: Optional[Dict[str, Any]] = None,
    ) -> None:
        if isinstance(settings, dict):
            settings = StorageDriverSettings(**settings)
        self._client = client
        self.client_configuration = client_configuration or {}
        self.bucket = settings.bucket
        self.lazy_driver = settings.lazy_driver
        if not (self.lazy_driver or client):
            self._client = self.build_client(self.client_configuration)

    @abc.abstractmethod
    def iterate_objects(
        self, prefix: Optional[str] = None
    ) -> Iterator[str]:  # pragma: no cover
        ...

    @abc.abstractmethod
    def upload_object(self, file_path: str, object_name: str):  # pragma: no cover
        ...

    @abc.abstractmethod
    def download_object(
        self, object_name: str, destination_path: str
    ):  # pragma: no cover
        ...

    @abc.abstractmethod
    def delete_object(self, object_name: str):  # pragma: no cover
        ...

    @abc.abstractmethod
    def exists(self, object_name: str) -> bool:  # pragma: no cover
        ...

    @abc.abstractmethod
    def get_object_uri(
        self, object_name: str, sub_part: Optional[str] = None
    ) -> str:  # pragma: no cover
        ...

    @property
    def client(self):
        return self._client or self.build_client(self.client_configuration)

    @staticmethod
    @abc.abstractmethod
    def build_client(client_configuration: Dict[str, Any]) -> Any:
        ...
