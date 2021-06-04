import copy
import hashlib
import pickle  # nosec
import typing
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    Type,
    Union,
)

import humanize
import pydantic
import sniffio
from asgiref.sync import AsyncToSync
from rich.console import Console
from rich.markup import escape
from rich.tree import Tree
from structlog import get_logger

import modelkit
from modelkit.core.settings import LibrarySettings
from modelkit.core.types import ItemType, ModelTestingConfiguration, ReturnType
from modelkit.utils.memory import PerformanceTracker
from modelkit.utils.pretty import describe, pretty_print_type
from modelkit.utils.pydantic import construct_recursive

logger = get_logger(__name__)


class NoModelDependenciesInInitError(BaseException):
    pass


class Asset:
    """
    Asset
    ===

    An asset is meant to be a way to share objects loaded onto memory.
    """

    CONFIGURATIONS: Dict[str, Dict[str, Any]] = {}

    def __init__(self, *args, **kwargs):
        """
        At init in the ModelLibrary, a Model is passed
        the `model` and `settings` parameters.
        `model` contains the paths to the assets
        `settings` a dictionary of parameters.

        :param args:
        :param kwargs:
        """
        self.configuration_key = kwargs.get("configuration_key")
        self.service_settings = kwargs.get("service_settings") or LibrarySettings()
        self.batch_size = kwargs.get("model_settings", {}).get("batch_size", 64)
        self.asset_path = kwargs.pop("asset_path", "")
        self.redis_cache = kwargs.pop("redis_cache", None)
        self._loaded = False
        self._deserializing = False
        self.model_settings = kwargs.pop("model_settings", {})
        self.load_time = None
        self.load_memory_increment = None

    def load(self):
        """Implement this method in order for the model to load and
        deserialize its asset, whose path is kept int the `asset_path`
        attribute"""
        self._deserializing = True
        with PerformanceTracker() as m:
            self._load()

        logger.debug(
            "Model loaded",
            model_name=self.configuration_key,
            time=humanize.naturaldelta(m.time, minimum_unit="microseconds"),
            time_s=m.time,
            memory=humanize.naturalsize(m.increment)
            if m.increment is not None
            else None,
            memory_bytes=m.increment,
        )
        self._loaded = True
        self._deserializing = False
        self.load_time = m.time
        self.load_memory_increment = m.increment

    def _load(self):
        pass


class InternalDataModel(pydantic.BaseModel):
    data: Any

    class Config:
        arbitrary_types_allowed = True
        extra = "forbid"


PYDANTIC_ERROR_TRUNCATION = 20


class ModelkitDataValidationException(Exception):
    def __init__(
        self,
        model_identifier,
        pydantic_exc=None,
        error_str="Data validation error in model",
    ):
        pydantic_exc_output = ""
        if pydantic_exc:
            exc_lines = str(pydantic_exc).split("\n")
            if len(exc_lines) > PYDANTIC_ERROR_TRUNCATION:
                pydantic_exc_output += "Pydantic error message "
                pydantic_exc_output += (
                    f"(truncated to {PYDANTIC_ERROR_TRUNCATION} lines):\n"
                )
                pydantic_exc_output += "\n".join(exc_lines[:PYDANTIC_ERROR_TRUNCATION])
                pydantic_exc_output += (
                    f"\n({len(exc_lines)-PYDANTIC_ERROR_TRUNCATION} lines truncated)"
                )
            else:
                pydantic_exc_output += "Pydantic error message:\n"
                pydantic_exc_output += str(pydantic_exc)

        super().__init__(f"{error_str} `{model_identifier}`.\n" + pydantic_exc_output)


class ValidationInitializationException(ModelkitDataValidationException):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            error_str="Exception when setting up pydantic validation models",
            pydantic_exc=kwargs.pop("pydantic_exc"),
        )


class ReturnValueValidationException(ModelkitDataValidationException):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            error_str="Return value validation error when calling model",
            pydantic_exc=kwargs.pop("pydantic_exc"),
        )


class ItemValidationException(ModelkitDataValidationException):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            error_str="Predict item validation error when calling model",
            pydantic_exc=kwargs.pop("pydantic_exc"),
        )


class BaseModel(Asset, Generic[ItemType, ReturnType]):
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

    # The correct type below raises an error with pydantic after version 0.18
    # TEST_CASES: Union[ModelTestingConfiguration[ItemType, ReturnType], Dict]
    TEST_CASES: Any

    def __init__(self, *args, **kwargs):
        self._model_dependencies = kwargs.pop("model_dependencies", {})
        self._model_cache_key = None
        self._item_model = None
        self._return_model = None
        super().__init__(self, *args, **kwargs)
        self.initialize_validation_models()

    def load(self):
        """For Model instances, there may be a need to also load the dependencies"""
        for m in self._model_dependencies.values():
            if not m._loaded:
                m.load()
        Asset.load(self)

    @property
    def model_dependencies(self):
        if not hasattr(self, "_loaded") or not self._loaded and not self._deserializing:
            raise NoModelDependenciesInInitError(
                "Model dependencies are not loaded yet!"
                "If you have to refer to it in the __init__ of the Model,"
                "move the code to the _load method."
            )
        return self._model_dependencies

    def initialize_validation_models(self):
        try:
            # Get the values of the T and V types
            generic_aliases = [
                t
                for t in self.__orig_bases__
                if isinstance(t, typing._GenericAlias)
                and issubclass(t.__origin__, Model)
            ]
            if len(generic_aliases):
                item_type, return_type = generic_aliases[0].__args__
                if item_type != ItemType:
                    self.item_type = item_type
                    type_name = self.__class__.__name__ + "ItemTypeModel"
                    self._item_model = pydantic.create_model(
                        type_name,
                        #  The order of the Union arguments matter here, in order
                        #  to make sure that lists of items and single items
                        # are correctly validated
                        data=(self.item_type, ...),
                        __base__=InternalDataModel,
                    )
                if return_type != ReturnType:
                    self.return_type = return_type
                    type_name = self.__class__.__name__ + "ReturnTypeModel"
                    self._return_type = Union[List[return_type], return_type]
                    self._return_model = pydantic.create_model(
                        type_name,
                        data=(self.return_type, ...),
                        __base__=InternalDataModel,
                    )
        except Exception as exc:
            raise ValidationInitializationException(
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

    def item_cache_key(self, item: Any, kwargs: Dict[str, Any]):
        if not self._model_cache_key:
            self._model_cache_key = (
                self.configuration_key + modelkit.__version__
            ).encode()
        pickled = pickle.dumps((item, kwargs))  # nosec: only used to build a hash
        return hashlib.sha256(self._model_cache_key + pickled).digest()

    @classmethod
    def _iterate_test_cases(cls, model_keys=None):
        if not hasattr(cls, "TEST_CASES"):
            logger.debug("No TEST_CASES defined", model_type=cls.__name__)
            return
        if isinstance(cls.TEST_CASES, dict):
            # This used to be OK with type instantiation but fails with a pydantic
            # error since 1.18
            # test_cases = ModelTestingConfiguration[ItemType, ReturnType]
            test_cases = ModelTestingConfiguration(**cls.TEST_CASES)
        else:
            test_cases = cls.TEST_CASES
        model_keys = model_keys or test_cases.model_keys or cls.CONFIGURATIONS.keys()
        for model_key in model_keys:
            for case in test_cases.cases:
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

        if (
            hasattr(self, "item_type")
            and hasattr(self, "return_type")
            and self.item_type
            and self.return_type
        ):
            sub_t = t.add(
                f"[deep_sky_blue1]signature[/deep_sky_blue1]: "
                f"{pretty_print_type(self.item_type)} ->"
                f" {pretty_print_type(self.item_type)}"
            )

        if self.load_time:
            sub_t = t.add(
                "[deep_sky_blue1]load time[/deep_sky_blue1]: [orange3]"
                + humanize.naturaldelta(self.load_time, minimum_unit="microseconds")
            )

        if self.load_memory_increment is not None:
            sub_t = t.add(
                f"[deep_sky_blue1]load memory[/deep_sky_blue1]: "
                f"[orange3]{humanize.naturalsize(self.load_memory_increment)}"
            )
        if self.model_dependencies:
            dep_t = t.add("[deep_sky_blue1]dependencies")
            for m in self.model_dependencies:
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
        exception: Type[ModelkitDataValidationException],
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

    def _validate_batch(
        self,
        items: List[Any],
        model: Union[Type[InternalDataModel], None],
        exception: Type[ModelkitDataValidationException],
    ):
        if model:
            try:
                if self.service_settings.enable_validation:
                    items = [model(data=item).data for item in items]
                else:
                    items = [
                        construct_recursive(model, data=item).data for item in items
                    ]
            except pydantic.error_wrappers.ValidationError as exc:
                raise exception(
                    f"{self.__class__.__name__}[{self.configuration_key}]",
                    pydantic_exc=exc,
                )
        return items

    def predict(self, item: ItemType, **kwargs):
        raise NotImplementedError()

    def test(self):
        console = Console()
        for i, (model_key, item, expected, keyword_args) in enumerate(
            self._iterate_test_cases(model_keys=[self.configuration_key])
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


class Model(BaseModel[ItemType, ReturnType]):
    def load(self):
        super().load()
        try:
            sniffio.current_async_library()
        except sniffio.AsyncLibraryNotFoundError:
            # In a synchronous context, we wrap asynchronous models
            # such that we can evaluate `.predict`
            # Otherwise, they will have to be awaited
            for model_name, m in self._model_dependencies.items():
                if isinstance(m, AsyncModel):
                    self._model_dependencies[model_name] = WrappedAsyncModel(m)

    def __call__(
        self,
        item: ItemType,
        _force_compute: bool = False,
        **kwargs,
    ) -> ReturnType:
        return self.predict(item, _force_compute=_force_compute, **kwargs)

    def _predict(self, item: ItemType, **kwargs) -> ReturnType:
        result = self._predict_batch([item], **kwargs)
        return result[0]

    def predict(
        self,
        item: ItemType,
        _force_compute: bool = False,
        **kwargs,
    ) -> ReturnType:
        return next(
            self.predict_gen(iter((item,)), _force_compute=_force_compute, **kwargs)
        )

    def predict_gen(
        self,
        items: Iterator[ItemType],
        batch_size: int = None,
        _force_compute: bool = False,
        _callback: Callable = None,
        **kwargs,
    ) -> Iterator[ReturnType]:
        batch_size = batch_size or self.batch_size
        batch: List[ItemType] = []
        step = 0
        while True:
            try:
                if len(batch) == batch_size:
                    yield from self._predict_single_batch_gen(
                        step,
                        batch,
                        _force_compute=_force_compute,
                        _callback=_callback,
                        **kwargs,
                    )
                    step += batch_size
                    batch = []
                else:
                    batch.append(next(items))
            except StopIteration:
                break
        if batch:
            yield from self._predict_single_batch_gen(
                step,
                batch,
                _force_compute=_force_compute,
                _callback=_callback,
                **kwargs,
            )

    def predict_batch(
        self,
        items: List[ItemType],
        _callback: Callable = None,
        batch_size: int = None,
        _force_compute: bool = False,
        **kwargs,
    ) -> List[ReturnType]:
        return list(
            self.predict_gen(
                iter(items),
                _callback=_callback,
                batch_size=batch_size,
                _force_compute=_force_compute,
                **kwargs,
            )
        )

    def _predict_single_batch_gen(
        self,
        _step: int,
        items: List[ItemType],
        _force_compute: bool = False,
        _callback: Callable = None,
        **kwargs,
    ) -> Iterator[ReturnType]:
        items = self._validate_batch(items, self._item_model, ItemValidationException)
        if self.redis_cache and self.model_settings.get("cache_predictions"):
            # In the case where cache is activated, sieve through
            # individual items
            results = []
            to_compute = []
            for kitem, item in enumerate(items):
                key = self.item_cache_key(item, kwargs)
                if not _force_compute and self.redis_cache.exists(key):
                    # We trust the data coming from Redis as it's a local cache
                    unpickled = pickle.loads(self.redis_cache.get(key))  # nosec
                    results.append(unpickled)
                else:
                    results.append(None)
                    to_compute.append((kitem, key, item))
            computed_results = self._predict_batch(
                [item[2] for item in to_compute],
                **kwargs,
            )
            for ((kitem, key, _), result) in zip(to_compute, computed_results):
                self.redis_cache.set(key, pickle.dumps(result))
                results[kitem] = result
            logger.debug(
                "Caching digest",
                recomputed=len(computed_results),
                from_cache=(len(results) - len(computed_results)),
                model=self.configuration_key,
            )
        else:
            # general case: items is a list of items to treat
            # if there are multiple examples but no batching
            # or if there are multiple examples and batching
            results = self._validate_batch(
                self._predict_batch(
                    items,
                    **kwargs,
                ),
                self._return_model,
                ReturnValueValidationException,
            )
        if _callback:
            _callback(_step, items, results)
        yield from results

    def _predict_batch(self, items: List[ItemType], **kwargs) -> List[ReturnType]:
        return [self._predict(p, **kwargs) for p in items]


class AsyncModel(BaseModel[ItemType, ReturnType]):
    async def __call__(
        self,
        item: ItemType,
        _force_compute: bool = False,
        **kwargs,
    ) -> ReturnType:
        return await self.predict(item, _force_compute=_force_compute, **kwargs)

    async def _predict(self, item: ItemType, **kwargs) -> ReturnType:
        result = await self._predict_batch([item], **kwargs)
        return result[0]

    async def predict(
        self,
        item: ItemType,
        _force_compute: bool = False,
        **kwargs,
    ) -> ReturnType:
        async for r in self.predict_gen(
            iter((item,)), _force_compute=_force_compute, **kwargs
        ):
            break
        return r

    async def predict_gen(
        self,
        items: Iterator[ItemType],
        batch_size: int = None,
        _force_compute: bool = False,
        _callback: Callable = None,
        **kwargs,
    ) -> AsyncIterator[ReturnType]:
        batch_size = batch_size or self.batch_size
        batch: List[ItemType] = []
        step = 0
        while True:
            try:
                if len(batch) == batch_size:
                    async for r in self._predict_single_batch_gen(
                        step,
                        batch,
                        _force_compute=_force_compute,
                        _callback=_callback,
                        **kwargs,
                    ):
                        yield r
                    step += batch_size
                    batch = []
                else:
                    batch.append(next(items))
            except StopIteration:
                break
        if batch:
            async for r in self._predict_single_batch_gen(
                step,
                batch,
                _force_compute=_force_compute,
                _callback=_callback,
                **kwargs,
            ):
                yield r

    async def predict_batch(
        self,
        items: List[ItemType],
        _callback: Callable = None,
        batch_size: int = None,
        _force_compute: bool = False,
        **kwargs,
    ) -> List[ReturnType]:
        return [
            r
            async for r in self.predict_gen(
                iter(items),
                _callback=_callback,
                batch_size=batch_size,
                _force_compute=_force_compute,
                **kwargs,
            )
        ]

    async def _predict_single_batch_gen(
        self,
        _step: int,
        items: List[ItemType],
        _force_compute: bool = False,
        _callback: Callable = None,
        **kwargs,
    ) -> AsyncIterator[ReturnType]:
        items = self._validate_batch(items, self._item_model, ItemValidationException)
        if self.redis_cache and self.model_settings.get("cache_predictions"):
            # In the case where cache is activated, sieve through
            # individual items
            results = []
            to_compute = []
            for kitem, item in enumerate(items):
                key = self.item_cache_key(item, kwargs)
                if not _force_compute and self.redis_cache.exists(key):
                    # We trust the data coming from Redis as it's a local cache
                    unpickled = pickle.loads(self.redis_cache.get(key))  # nosec
                    results.append(unpickled)
                else:
                    results.append(None)
                    to_compute.append((kitem, key, item))
            computed_results = await self._predict_batch(
                [item[2] for item in to_compute],
                **kwargs,
            )
            for ((kitem, key, _), result) in zip(to_compute, computed_results):
                self.redis_cache.set(key, pickle.dumps(result))
                results[kitem] = result
            logger.debug(
                "Caching digest",
                recomputed=len(computed_results),
                from_cache=(len(results) - len(computed_results)),
                model=self.configuration_key,
            )
        else:
            # general case: items is a list of items to treat
            # if there are multiple examples but no batching
            # or if there are multiple examples and batching
            results = self._validate_batch(
                await self._predict_batch(
                    items,
                    **kwargs,
                ),
                self._return_model,
                ReturnValueValidationException,
            )
        if _callback:
            _callback(_step, items, results)
        for r in results:
            yield r

    async def _predict_batch(self, items: List[ItemType], **kwargs) -> List[ReturnType]:
        return [await self._predict(p, **kwargs) for p in items]


class WrappedAsyncModel:
    def __init__(self, async_model: AsyncModel):
        self.async_model = async_model
        self.predict = AsyncToSync(self.async_model.predict)
        self.predict_batch = AsyncToSync(self.async_model.predict_batch)
