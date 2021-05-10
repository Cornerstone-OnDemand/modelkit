from typing import (
    Any,
    ByteString,
    Dict,
    Generic,
    List,
    Mapping,
    Optional,
    Set,
    TypeVar,
    Union,
)

import pydantic
import pydantic.generics

ALLOWED_ITEM_TYPES = Union[
    str, int, float, Mapping, Set, ByteString, pydantic.BaseModel
]

ItemType = TypeVar("ItemType", bound=ALLOWED_ITEM_TYPES)
ReturnType = TypeVar("ReturnType")


TestReturnType = TypeVar("TestReturnType")
TestItemType = TypeVar("TestItemType")


class TestCases(pydantic.generics.GenericModel, Generic[TestItemType, TestReturnType]):
    item: TestItemType
    result: TestReturnType
    keyword_args: Dict[str, Any] = {}


class ModelTestingConfiguration(
    pydantic.generics.GenericModel, Generic[TestItemType, TestReturnType]
):
    model_keys: Optional[List[str]]
    cases: List[TestCases[TestItemType, TestReturnType]]
