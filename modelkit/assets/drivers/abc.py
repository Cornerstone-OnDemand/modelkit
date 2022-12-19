import abc
from typing import Iterator, Optional


class StorageDriver(abc.ABC):
    bucket: str

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
