from typing import Any, Dict, Generic, List, Optional, TypeVar

import pydantic
import pydantic.generics

ItemType = TypeVar("ItemType")
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
