import abc
from typing import Iterator, Optional


class StorageDriver(abc.ABC):
    bucket: str

    def iterate_objects(
        self, prefix: Optional[str] = None
    ) -> Iterator[str]:  # pragma: no cover
        ...

    def upload_object(self, file_path: str, object_name: str):  # pragma: no cover
        ...

    def download_object(
        self, object_name: str, destination_path: str
    ):  # pragma: no cover
        ...

    def delete_object(self, object_name: str):  # pragma: no cover
        ...

    def exists(self, object_name: str) -> bool:  # pragma: no cover
        ...

    def get_object_uri(
        self, object_name: str, sub_part: Optional[str] = None
    ) -> str:  # pragma: no cover
        ...
