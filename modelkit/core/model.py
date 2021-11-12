import copy
import enum
import typing
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

import humanize
import pydantic
import sniffio
from asgiref.sync import AsyncToSync
from rich.console import Console
from rich.markup import escape
from rich.tree import Tree
from structlog import get_logger
from typing_extensions import Protocol

from modelkit.core import errors
from modelkit.core.settings import LibrarySettings
from modelkit.core.types import ItemType, ReturnType, TestCase
from modelkit.utils.cache import Cache, CacheItem
from modelkit.utils.memory import PerformanceTracker
from modelkit.utils.pretty import describe, pretty_print_type
from modelkit.utils.pydantic import construct_recursive

logger = get_logger(__name__)

ModelDependency = TypeVar(
    "ModelDependency", bound=Union["Model", "AsyncModel", "WrappedAsyncModel"]
)


class ModelDependenciesMapping:
    def __init__(self, models: Optional[Dict[str, ModelDependency]] = None):
        self.models = models or {}

    def __getitem__(self, key: str) -> ModelDependency:
        return self.models[key]

    def get(
        self, key: str, model_type: Optional[Type[ModelDependency]] = None
    ) -> ModelDependency:
        m = self.models[key]
        if model_type and not isinstance(m, model_type):
            raise ValueError(f"Model `{m}` is not an instance of {model_type}")
        return cast(ModelDependency, m)

    def items(self):
        return self.models.items()

    def values(self):
        return self.models.values()

    def keys(self):
        return self.models.keys()

    def __iter__(self):
        return self.models.__iter__()

    def __len__(self):
        return len(self.models)


class Asset:
    """
    Asset
    ===

    An asset is meant to be a way to share objects loaded onto memory.
    """

    CONFIGURATIONS: Dict[str, Dict[str, Any]] = {}

    def __init__(
        self,
        configuration_key: Optional[str] = None,
        service_settings: Optional[LibrarySettings] = None,
        model_settings: Optional[Dict[str, Any]] = None,
        asset_path: str = "",
        cache: Optional[Cache] = None,
        batch_size: Optional[int] = None,
        model_dependencies: Optional[
            Dict[str, Union["Model", "AsyncModel", "WrappedAsyncModel"]]
        ] = None,
    ):
        """
        At init in the ModelLibrary, a Model is passed
        the `model` and `settings` parameters.
        `model` contains the paths to the assets
        `settings` a dictionary of parameters.

        :param args:
        :param kwargs:
        """
        self.configuration_key: Optional[str] = configuration_key
        self.service_settings: LibrarySettings = service_settings or LibrarySettings()
        self.asset_path: str = asset_path
        self.cache: Optional[Cache] = cache
        self.model_settings: Dict[str, Any] = model_settings or {}
        self.batch_size: Optional[int] = batch_size or self.model_settings.get(
            "batch_size"
        )
        self.model_dependencies: ModelDependenciesMapping = ModelDependenciesMapping(
            model_dependencies or {}
        )

        self._loaded: bool = False
        self._load_time: Optional[float] = None
        self._load_memory_increment: Optional[float] = None

        if not self.service_settings.lazy_loading:
            self.load()

    def load(self) -> None:
        """Implement this method in order for the model to load and
        deserialize its asset, whose path is kept int the `asset_path`
        attribute"""
        with PerformanceTracker() as m:
            self._load()

        logger.debug(
            "Model loaded",
            model_name=self.configuration_key,
            time=humanize.naturaldelta(m.time, minimum_unit="seconds"),
            time_s=m.time,
            memory=humanize.naturalsize(m.increment)
            if m.increment is not None
            else None,
            memory_bytes=m.increment,
        )
        self._loaded = True
        self._load_time = m.time
        self._load_memory_increment = m.increment

    def _load(self) -> None:
        pass


class InternalDataModel(pydantic.BaseModel):
    data: Any

    class Config:
        arbitrary_types_allowed = True
        extra = "forbid"


PYDANTIC_ERROR_TRUNCATION = 20


class AbstractModel(Asset, Generic[ItemType, ReturnType]):
    """
    Model
    ===

    A Model is an Asset that implements some algorithm and serves it via `.predict`

    the Model class ensures that predictions are logged,
     timed and formatted properly.

    To implement a Model, either implement
    _predict or _predict_batch
    that either take items or lists of items.
    """

    TEST_CASES: List[Union[TestCase[ItemType, ReturnType], Dict]]

    def __init__(
        self,
        **kwargs,
    ):
        self._item_model: Optional[Type[InternalDataModel]] = None
        self._return_model: Optional[Type[InternalDataModel]] = None
        self._item_type: Optional[Type] = None
        self._return_type: Optional[Type] = None
        self._loaded: bool = False
        self._predict_mode: Optional[PredictMode] = None
        super().__init__(**kwargs)
        self.initialize_validation_models()
        self._check_is_overriden()

    def load(self):
        """For Model instances, there may be a need to also load the dependencies"""
        for m in self.model_dependencies.values():
            if not m._loaded:
                m.load()
        Asset.load(self)

    def initialize_validation_models(self):
        try:
            # Get the values of the T and V types
            generic_aliases = [
                t
                for t in self.__orig_bases__
                if isinstance(t, typing._GenericAlias)
                and issubclass(t.__origin__, AbstractModel)
            ]
            if len(generic_aliases):
                _item_type, _return_type = generic_aliases[0].__args__
                if _item_type != ItemType:
                    self._item_type = _item_type
                    type_name = self.__class__.__name__ + "ItemTypeModel"
                    self._item_model = pydantic.create_model(
                        type_name,
                        #  The order of the Union arguments matter here, in order
                        #  to make sure that lists of items and single items
                        # are correctly validated
                        data=(self._item_type, ...),
                        __base__=InternalDataModel,
                    )
                if _return_type != ReturnType:
                    self._return_type = _return_type
                    type_name = self.__class__.__name__ + "ReturnTypeModel"
                    self._return_model = pydantic.create_model(
                        type_name,
                        data=(self._return_type, ...),
                        __base__=InternalDataModel,
                    )
        except Exception as exc:  # pragma: no cover
            raise errors.ValidationInitializationException(
                f"{self.__class__.__name__}[{self.configuration_key}]", pydantic_exc=exc
            )

    def __getstate__(self):
        state = copy.deepcopy(self.__dict__)
        state["_item_model"] = None
        state["_return_model"] = None
        return state

    def __setstate__(self, state):
        self.__dict__ = state
        self.initialize_validation_models()

    @classmethod
    def _iterate_test_cases(cls, model_key: Optional[str] = None):
        if (
            not hasattr(cls, "TEST_CASES")
            and not (
                model_key
                or any("test_cases" in conf for conf in cls.CONFIGURATIONS.values())
            )
            and (model_key and "test_cases" not in cls.CONFIGURATIONS[model_key])
        ) or (model_key and model_key not in cls.CONFIGURATIONS):
            logger.debug("No test cases defined", model_type=cls.__name__)
            return

        model_keys = [model_key] if model_key else cls.CONFIGURATIONS.keys()
        cls_test_cases: List[Union[TestCase[ItemType, ReturnType], Dict]] = []

        if hasattr(cls, "TEST_CASES"):
            cls_test_cases = cls.TEST_CASES

        for model_key in model_keys:
            for case in cls_test_cases:
                if isinstance(case, dict):
                    case = TestCase(**case)
                yield model_key, case.item, case.result, case.keyword_args

            conf = cls.CONFIGURATIONS[model_key]
            if "test_cases" not in conf:
                continue
            for case in conf["test_cases"]:
                if isinstance(case, dict):
                    case = TestCase(**case)
                yield model_key, case.item, case.result, case.keyword_args

    def describe(self, t=None):
        if not t:
            t = Tree("")

        if self.configuration_key:
            sub_t = t.add(
                f"[deep_sky_blue1]configuration[/deep_sky_blue1]: "
                f"[orange3]{self.configuration_key}"
            )

        if self.__doc__:
            t.add(f"[deep_sky_blue1]doc[/deep_sky_blue1]: {self.__doc__.strip()}")

        if self._item_type and self._return_type:
            sub_t = t.add(
                f"[deep_sky_blue1]signature[/deep_sky_blue1]: "
                f"{pretty_print_type(self._item_type)} ->"
                f" {pretty_print_type(self._return_type)}"
            )

        if self._load_time:
            sub_t = t.add(
                "[deep_sky_blue1]load time[/deep_sky_blue1]: [orange3]"
                + humanize.naturaldelta(self._load_time, minimum_unit="seconds")
            )

        if self._load_memory_increment is not None:
            sub_t = t.add(
                f"[deep_sky_blue1]load memory[/deep_sky_blue1]: "
                f"[orange3]{humanize.naturalsize(self._load_memory_increment)}"
            )
        if self.model_dependencies.models:
            dep_t = t.add("[deep_sky_blue1]dependencies")
            for m in self.model_dependencies.models:
                dep_t.add("[orange3]" + escape(m))

        if self.asset_path:
            sub_t = t.add(
                f"[deep_sky_blue1]asset path[/deep_sky_blue1]: "
                f"[orange3]{self.asset_path}"
            )

        if self.batch_size:
            sub_t = t.add(
                f"[deep_sky_blue1]batch size[/deep_sky_blue1]: "
                f"[orange3]{self.batch_size}"
            )
        if self.model_settings:
            sub_t = t.add("[deep_sky_blue1]model settings[/deep_sky_blue1]")
            describe(self.model_settings, t=sub_t)

        return t

    def _validate(
        self,
        item: Any,
        model: Union[Type[InternalDataModel], None],
        exception: Type[errors.ModelkitDataValidationException],
    ):
        if model:
            try:
                if self.service_settings.enable_validation:
                    return model(data=item).data
                else:
                    return construct_recursive(model, data=item).data
            except pydantic.error_wrappers.ValidationError as exc:
                raise exception(
                    f"{self.__class__.__name__}[{self.configuration_key}]",
                    pydantic_exc=exc,
                )
        return item

    def test(self):
        console = Console()
        for i, (model_key, item, expected, keyword_args) in enumerate(
            self._iterate_test_cases(model_key=self.configuration_key)
        ):
            result = None
            try:
                if isinstance(self, AsyncModel):
                    result = AsyncToSync(self.predict)(item, **keyword_args)
                else:
                    result = self.predict(item, **keyword_args)
                assert result == expected
                console.print(f"[green]TEST {i+1}: SUCCESS[/green]")
            except AssertionError:
                console.print(
                    "[red]TEST {}: FAILED[/red]{} test failed on item".format(
                        i + 1, " [" + model_key + "]" if model_key else ""
                    )
                )
                t = Tree("item")
                console.print(describe(item, t=t))
                t = Tree("expected")
                console.print(describe(expected, t=t))
                t = Tree("result")
                console.print(describe(result, t=t))
                raise

    def _check_is_overriden(self):
        if not hasattr(self._predict, "__not_overriden__"):
            self._predict_mode = PredictMode.SINGLE
        if not hasattr(self._predict_batch, "__not_overriden__"):
            if self._predict_mode == PredictMode.SINGLE:
                raise BothPredictsOverridenError(
                    "_predict OR _predict_batch must be overriden, not both"
                )
            self._predict_mode = PredictMode.BATCH
        if not self._predict_mode:
            raise NoPredictOverridenError(
                "_predict or _predict_batch must be overriden"
            )


class CallableWithAttribute(Protocol):
    __call__: Callable
    __not_overriden__: Optional[bool]


def not_overriden(func: Callable) -> CallableWithAttribute:
    # Decorating with an attribute while preserving
    # typing is slightly tricky
    # https://github.com/python/mypy/issues/2087

    func_with_attributes = cast(CallableWithAttribute, func)
    func_with_attributes.__not_overriden__ = True
    return func_with_attributes


class PredictMode(enum.Enum):
    SINGLE = 1
    BATCH = 1


class BothPredictsOverridenError(Exception):
    pass


class NoPredictOverridenError(Exception):
    pass


class Model(AbstractModel[ItemType, ReturnType]):
    def load(self):
        super().load()
        try:
            sniffio.current_async_library()
        except sniffio.AsyncLibraryNotFoundError:
            # In a synchronous context, we wrap asynchronous models
            # such that we can evaluate `.predict`
            # Otherwise, they will have to be awaited
            _model_dependencies = {}
            for model_name, m in self.model_dependencies.items():
                if isinstance(m, AsyncModel):
                    _model_dependencies[model_name] = WrappedAsyncModel(m)
                else:
                    _model_dependencies[model_name] = m
            self.model_dependencies = ModelDependenciesMapping(_model_dependencies)

    @not_overriden
    def _predict(self, item: ItemType, **kwargs) -> ReturnType:  # pragma: no cover
        ...

    @not_overriden
    def _predict_batch(self, items: List[ItemType], **kwargs) -> List[ReturnType]:
        return [self._predict(p, **kwargs) for p in items]

    @errors.wrap_modelkit_exceptions
    def __call__(
        self,
        item: ItemType,
        _force_compute: bool = False,
        **kwargs,
    ) -> ReturnType:
        return self.predict(
            item, _force_compute=_force_compute, __internal=True, **kwargs
        )

    @errors.wrap_modelkit_exceptions
    def predict(
        self,
        item: ItemType,
        _force_compute: bool = False,
        **kwargs,
    ) -> ReturnType:
        return next(
            self.predict_gen(
                iter((item,)), _force_compute=_force_compute, __internal=True, **kwargs
            )
        )

    @errors.wrap_modelkit_exceptions
    def predict_batch(
        self,
        items: List[ItemType],
        _callback: Optional[
            Callable[[int, List[ItemType], Iterator[ReturnType]], None]
        ] = None,
        batch_size: Optional[int] = None,
        _force_compute: bool = False,
        **kwargs,
    ) -> List[ReturnType]:
        batch_size = batch_size or (self.batch_size or len(items))
        return list(
            self.predict_gen(
                iter(items),
                _callback=_callback,
                batch_size=batch_size,
                _force_compute=_force_compute,
                __internal=True,
                **kwargs,
            )
        )

    @errors.wrap_modelkit_exceptions_gen
    def predict_gen(
        self,
        items: Iterator[ItemType],
        batch_size: Optional[int] = None,
        _callback: Optional[
            Callable[[int, List[ItemType], Iterator[ReturnType]], None]
        ] = None,
        _force_compute: bool = False,
        **kwargs,
    ) -> Iterator[ReturnType]:
        batch_size = batch_size or (self.batch_size or 1)
        n_items_to_compute = 0
        n_items_from_cache = 0
        cache_items: List[CacheItem] = []
        step = 0
        for current_item in items:
            # This loops creates a list of `CacheItems` which
            # wrap the items with information as to their
            # status within the cache.
            # Whenever `cache_items` has `batch_size` elements that need
            # to be recomputed, `_predict_cache_items` is called, which will
            # in turn yield all results in the correct order.
            # Once we have 2 x batch_size elements available from cache
            # we yield them to avoid indefinite increase in the cache_item
            # list size.
            if (
                self.configuration_key
                and self.cache
                and self.model_settings.get("cache_predictions")
            ):
                if not _force_compute:
                    # The cache will return a CacheItem with the information
                    # as to the stored value (if it exists) and if it is missing
                    # the cache_key needed to store it
                    cache_item = self.cache.get(
                        self.configuration_key, current_item, kwargs
                    )
                else:
                    # When force_recomputing, we still need to get
                    # the cache key
                    cache_item = CacheItem(
                        current_item,
                        self.cache.hash_key(
                            self.configuration_key, current_item, kwargs
                        ),
                        None,
                        True,
                    )
                if cache_item.missing:
                    n_items_to_compute += 1
                else:
                    n_items_from_cache += 1
                cache_items.append(cache_item)
            else:
                # When no cache is active, all of them should be computed
                cache_items.append(CacheItem(current_item, None, None, True))
                n_items_to_compute += 1
            if batch_size and (
                n_items_to_compute == batch_size or n_items_from_cache == 2 * batch_size
            ):
                yield from self._predict_cache_items(
                    step, cache_items, _callback=_callback, **kwargs
                )
                cache_items = []
                n_items_to_compute = 0
                n_items_from_cache = 0
                step += batch_size

        if cache_items:
            yield from self._predict_cache_items(
                step, cache_items, _callback=_callback, **kwargs
            )

    def _predict_cache_items(
        self,
        _step: int,
        cache_items: List[CacheItem],
        _callback: Optional[
            Callable[[int, List[ItemType], Iterator[ReturnType]], None]
        ] = None,
        **kwargs,
    ) -> Iterator[ReturnType]:
        batch = [
            self._validate(res.item, self._item_model, errors.ItemValidationException)
            for res in cache_items
            if res.missing
        ]
        try:
            predictions = iter(self._predict_batch(batch, **kwargs))
        except BaseException as exc:
            raise errors.PredictionError(exc=exc)
        for cache_item in cache_items:
            if cache_item.missing:
                r = next(predictions)
                if (
                    cache_item.cache_key
                    and self.configuration_key
                    and self.cache
                    and self.model_settings.get("cache_predictions")
                ):
                    self.cache.set(cache_item.cache_key, r)
                yield self._validate(
                    r,
                    self._return_model,
                    errors.ReturnValueValidationException,
                )
            else:
                yield self._validate(
                    cache_item.cache_value,
                    self._return_model,
                    errors.ReturnValueValidationException,
                )
        if _callback:
            _callback(_step, batch, predictions)

    def close(self):
        pass


class AsyncModel(AbstractModel[ItemType, ReturnType]):
    @not_overriden
    async def _predict(
        self, item: ItemType, **kwargs
    ) -> ReturnType:  # pragma: no cover
        ...

    @not_overriden
    async def _predict_batch(self, items: List[ItemType], **kwargs) -> List[ReturnType]:
        return [await self._predict(p, **kwargs) for p in items]

    @errors.wrap_modelkit_exceptions_async
    async def __call__(
        self,
        item: ItemType,
        _force_compute: bool = False,
        **kwargs,
    ) -> ReturnType:
        return await self.predict(
            item, _force_compute=_force_compute, __internal=True, **kwargs
        )

    @errors.wrap_modelkit_exceptions_async
    async def predict(
        self,
        item: ItemType,
        _force_compute: bool = False,
        **kwargs,
    ) -> ReturnType:
        async for r in self.predict_gen(
            iter((item,)), _force_compute=_force_compute, __internal=True, **kwargs
        ):
            break
        return r

    @errors.wrap_modelkit_exceptions_async
    async def predict_batch(
        self,
        items: List[ItemType],
        _callback: Optional[
            Callable[[int, List[ItemType], Iterator[ReturnType]], None]
        ] = None,
        batch_size: Optional[int] = None,
        _force_compute: bool = False,
        **kwargs,
    ) -> List[ReturnType]:
        batch_size = batch_size or (self.batch_size or len(items))
        return [
            r
            async for r in self.predict_gen(
                iter(items),
                _callback=_callback,
                batch_size=batch_size,
                _force_compute=_force_compute,
                __internal=True,
                **kwargs,
            )
        ]

    @errors.wrap_modelkit_exceptions_gen_async
    async def predict_gen(
        self,
        items: Iterator[ItemType],
        batch_size: Optional[int] = None,
        _callback: Optional[
            Callable[[int, List[ItemType], Iterator[ReturnType]], None]
        ] = None,
        _force_compute: bool = False,
        **kwargs,
    ) -> AsyncIterator[ReturnType]:
        batch_size = batch_size or (self.batch_size or 1)

        n_items_to_compute = 0
        n_items_from_cache = 0
        cache_items: List[CacheItem] = []
        step = 0
        for current_item in items:
            if (
                self.configuration_key
                and self.cache
                and self.model_settings.get("cache_predictions")
            ):
                if not _force_compute:
                    cache_item = self.cache.get(
                        self.configuration_key, current_item, kwargs
                    )
                else:
                    cache_item = CacheItem(
                        current_item,
                        self.cache.hash_key(
                            self.configuration_key, current_item, kwargs
                        ),
                        None,
                        True,
                    )
                if cache_item.missing:
                    n_items_to_compute += 1
                else:
                    n_items_from_cache += 1
                cache_items.append(cache_item)
            else:
                cache_items.append(CacheItem(current_item, None, None, True))
                n_items_to_compute += 1

            if batch_size and (
                n_items_to_compute == batch_size or n_items_from_cache == 2 * batch_size
            ):
                async for r in self._predict_cache_items(
                    step, cache_items, _callback=_callback, **kwargs
                ):
                    yield r
                cache_items = []
                n_items_to_compute = 0
                n_items_from_cache = 0
                step += batch_size

        if cache_items:
            async for r in self._predict_cache_items(
                step, cache_items, _callback=_callback, **kwargs
            ):
                yield r

    async def _predict_cache_items(
        self,
        _step: int,
        cache_items: List[CacheItem],
        _callback: Optional[
            Callable[[int, List[ItemType], Iterator[ReturnType]], None]
        ] = None,
        **kwargs,
    ) -> AsyncIterator[ReturnType]:
        batch = [
            self._validate(res.item, self._item_model, errors.ItemValidationException)
            for res in cache_items
            if res.missing
        ]
        try:
            predictions = iter(await self._predict_batch(batch, **kwargs))
        except BaseException as exc:
            raise errors.PredictionError(exc=exc)
        for cache_item in cache_items:
            if cache_item.missing:
                r = next(predictions)
                if (
                    cache_item.cache_key
                    and self.configuration_key
                    and self.cache
                    and self.model_settings.get("cache_predictions")
                ):
                    self.cache.set(cache_item.cache_key, r)
                yield self._validate(
                    r,
                    self._return_model,
                    errors.ReturnValueValidationException,
                )
            else:
                yield self._validate(
                    cache_item.cache_value,
                    self._return_model,
                    errors.ReturnValueValidationException,
                )
        if _callback:
            _callback(_step, batch, predictions)

    async def close(self):
        pass


class WrappedAsyncModel:
    def __init__(self, async_model: AsyncModel[ItemType, ReturnType]):
        self.async_model = async_model
        self.predict = AsyncToSync(self.async_model.predict)
        self.predict_batch = AsyncToSync(self.async_model.predict_batch)
        self._loaded: bool = True
        # The following does not currently work, because AsyncToSync does not
        # seem to correctly wrap asynchronous generators
        # self.predict_gen = AsyncToSync(self.async_model.predict_gen)
