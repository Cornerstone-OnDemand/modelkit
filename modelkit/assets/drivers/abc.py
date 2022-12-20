import abc
import os
from typing import Any, Dict, Iterator, Optional


class StorageDriver(abc.ABC):
    bucket: str

    def __init__(
        self,
        bucket: Optional[str],
        client: Optional[Any] = None,
        client_configuration: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__()
        self._client = client
        self.client_configuration = client_configuration or {}
        self.bucket = bucket or os.environ.get("MODELKIT_STORAGE_BUCKET") or ""
        if not self.bucket:
            raise ValueError("Bucket needs to be set for the storage driver")
        self.lazy_driver = os.environ.get("MODELKIT_LAZY_DRIVER")
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
