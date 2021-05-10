import asyncio
import copy
import hashlib
import json
import os
import pickle  # nosec
import typing
from typing import Any, Callable, Dict, Generic, List, Optional, Union, overload

import aiohttp
import numpy as np
import pydantic
import redis
import requests
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)

import modelkit
from modelkit.core.settings import ServiceSettings
from modelkit.core.types import ItemType, ModelTestingConfiguration, ReturnType
from modelkit.log import logger
from modelkit.utils.memory import log_memory_increment
from modelkit.utils.tensorflow import (
    TFServingError,
    make_serving_request,
    wait_local_serving,
)

try:
    import tensorflow as tf
    from tensorflow.python.saved_model.signature_constants import (
        DEFAULT_SERVING_SIGNATURE_DEF_KEY,
    )
    from tensorflow_serving.apis.predict_pb2 import PredictRequest

except ModuleNotFoundError:
    logger.info("tensorflow is not installed")


def _run_secretly_sync_async_fn(async_fn, *args, **kwargs):
    coro = async_fn(*args, **kwargs)
    try:
        coro.send(None)
    except StopIteration as exc:
        return exc.value
    else:
        raise RuntimeError("this async function is not secretly synchronous")


def _create_model_object(
    model_type,
    service_settings: ServiceSettings,
    asset_path: Optional[str] = None,
    model_dependencies: Optional[Union[List[str], Dict[str, str]]] = None,
    model_settings: Optional[Dict[str, Any]] = None,
    configuration_key: Optional[str] = None,
    redis_cache: Optional[redis.Redis] = None,
):
    m = model_type(
        asset_path=asset_path or "",
        model_dependencies=model_dependencies,
        service_settings=service_settings,
        model_settings=model_settings or {},
        configuration_key=configuration_key,
        redis_cache=redis_cache,
    )
    if not service_settings.lazy_loading:
        m.deserialize_asset()
    return m


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
        self.service_settings = kwargs.get("service_settings") or ServiceSettings()
        self.batch_size = kwargs.pop("batch_size", 64)
        self.model_classname = self.__class__.__name__
        self.asset_path = kwargs.pop("asset_path", "")
        self.redis_cache = kwargs.pop("redis_cache", None)
        self._loaded = False
        self._deserializing = False
        self.model_settings = kwargs.pop("model_settings", {})

    def deserialize_asset(self):
        """Implement this method in order for the model to load and
        deserialize its asset, whose path is kept int the `asset_path`
        attribute"""
        self._deserializing = True
        with log_memory_increment(
            self.model_classname
            + (f":{self.configuration_key}" if self.configuration_key else "")
        ):
            self._deserialize_asset()
        self._loaded = True
        self._deserializing = False

    def _deserialize_asset(self):
        pass

    @staticmethod
    def fit(*args, **kwargs):
        raise NotImplementedError()


class InternalDataModel(pydantic.BaseModel):
    class Config:
        arbitrary_types_allowed = True
        extra = "forbid"


PYDANTIC_ERROR_TRUNCATION = 20


class modelkitDataValidationException(Exception):
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


class ValidationInitializationException(modelkitDataValidationException):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            error_str="Exception when setting up pydantic validation models",
            pydantic_exc=kwargs.pop("pydantic_exc"),
        )


class ReturnValueValidationException(modelkitDataValidationException):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            error_str="Return value validation error when calling model",
            pydantic_exc=kwargs.pop("pydantic_exc"),
        )


class ItemValidationException(modelkitDataValidationException):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            error_str="Predict item validation error when calling model",
            pydantic_exc=kwargs.pop("pydantic_exc"),
        )


class Model(Asset, Generic[ItemType, ReturnType]):
    """
    Model
    ===

    A Model is an Asset that implements some algorithm and serves it via `.predict`

    the Model class ensures that predictions are logged,
     timed and formatted properly.

    To implement a Model, either implement
    _predict_one or _predict_multiple
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

    def deserialize_asset(self):
        """For Model instances, there may be a need to also load the dependencies"""
        for m in self._model_dependencies.values():
            if not m._loaded:
                m.deserialize_asset()
        Asset.deserialize_asset(self)

    @property
    def model_dependencies(self):
        if not hasattr(self, "_loaded") or not self._loaded and not self._deserializing:
            raise NoModelDependenciesInInitError(
                "Model dependencies are not loaded yet!"
                "If you have to refer to it in the __init__ of the Model,"
                "move the code to the _deserialize_asset method."
            )
        return self._model_dependencies

    def item_cache_key(self, item: Any, kwargs: Dict[str, Any]):
        if not self._model_cache_key:
            self._model_cache_key = (
                self.configuration_key + modelkit.__version__
            ).encode()
        pickled = pickle.dumps((item, kwargs))  # nosec: only used to build a hash
        return hashlib.sha256(self._model_cache_key + pickled).digest()

    @overload
    def predict(self, items: ItemType) -> ReturnType:
        ...

    @overload
    def predict(self, items: List[ItemType]) -> List[ReturnType]:
        ...

    def predict(
        self,
        items,
        callback: Callable = None,
        batch_size: int = None,
        **kwargs,
    ):
        return _run_secretly_sync_async_fn(
            self.predict_async, items, callback, batch_size, **kwargs
        )

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
                    type_name = self.__class__.__name__ + "ItemTypeModel"
                    self._item_model = pydantic.create_model(
                        type_name,
                        #  The order of the Union arguments matter here, in order
                        #  to make sure that lists of items and single items
                        # are correctly validated
                        data=(Union[List[item_type], item_type], ...),
                        __base__=InternalDataModel,
                    )
                if return_type != ReturnType:
                    type_name = self.__class__.__name__ + "ReturnTypeModel"
                    self._return_model = pydantic.create_model(
                        type_name,
                        data=(Union[List[return_type], return_type], ...),
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

    @overload
    async def predict_async(self, items: ItemType) -> ReturnType:
        ...

    @overload
    async def predict_async(self, items: List[ItemType]) -> List[ReturnType]:
        ...

    async def predict_async(
        self,
        items,
        callback: Callable = None,
        batch_size: int = None,
        _force_compute: bool = False,
        _return_info: bool = False,
        **kwargs,
    ):
        """
        Implement `Model._predict_one(item)` to make predictions
        and if there can be enhancements with batching, implement
        `Model._predict_multiple(items)`.
        They call each other so make sure that you do
        in fact implement one of them.
        """
        if self._item_model:
            try:
                items = self._item_model(data=items).data
            except pydantic.error_wrappers.ValidationError as exc:
                raise ItemValidationException(
                    f"{self.__class__.__name__}[{self.configuration_key}]",
                    pydantic_exc=exc,
                )
        from_cache = False
        # if it is called with a single example
        if not isinstance(items, list):
            if self.redis_cache and self.model_settings.get("cache_predictions"):
                key = self.item_cache_key(items, kwargs)
                if not _force_compute and self.redis_cache.exists(key):
                    from_cache = True
                    logger.debug(
                        "Prediction result fetched from cache",
                        key=key,
                        model=self.configuration_key,
                    )
                    results = pickle.loads(self.redis_cache.get(key))  # nosec
                else:
                    logger.debug(
                        "No cached prediction result found",
                        key=key,
                        model=self.configuration_key,
                    )
                    results = await self._predict_one(items, **kwargs)
                    self.redis_cache.set(key, pickle.dumps(results))
            else:
                results = await self._predict_one(items, **kwargs)
        elif self.redis_cache and self.model_settings.get("cache_predictions"):
            # In the case where cache is activated, sieve through
            #  individual items
            results = []
            to_compute = []
            for kitem, item in enumerate(items):
                key = self.item_cache_key(item, kwargs)
                if not _force_compute and self.redis_cache.exists(key):
                    # We trust the data coming from Redis as it's a local cache
                    unpickled = pickle.loads(self.redis_cache.get(key))  # nosec
                    if not _return_info:
                        results.append(unpickled)
                    else:
                        results.append((unpickled, True))
                else:
                    results.append(None)
                    to_compute.append((kitem, key, item))
            computed_results = await self._predict_by_batch(
                [item[2] for item in to_compute],
                batch_size=batch_size or self.batch_size,
                callback=callback,
                **kwargs,
            )
            for ((kitem, key, _), result) in zip(to_compute, computed_results):
                self.redis_cache.set(key, pickle.dumps(result))
                if not _return_info:
                    results[kitem] = result
                else:
                    results[kitem] = (result, False)
            logger.debug(
                "Caching digest",
                recomputed=len(computed_results),
                from_cache=(len(results) - len(computed_results)),
                model=self.configuration_key,
            )
            return results
        else:
            # general case: items is a list of items to treat
            # if there are multiple examples but no batching
            # or if there are multiple examples and batching
            results = await self._predict_by_batch(
                items,
                batch_size=batch_size or self.batch_size,
                callback=callback,
                **kwargs,
            )
        if self._return_model:
            try:
                results = self._return_model(data=results).data
            except pydantic.error_wrappers.ValidationError as exc:
                raise ReturnValueValidationException(
                    self.configuration_key, pydantic_exc=exc
                )
        if _return_info:
            return results, from_cache
        return results

    async def _predict_by_batch(
        self, items: List[ItemType], batch_size=64, callback=None, **kwargs
    ) -> List[ReturnType]:
        predictions = []
        for step in range(0, len(items), batch_size):
            batch = items[step : step + batch_size]
            current_predictions = await self._predict_multiple(batch, **kwargs)
            predictions.extend(current_predictions)
            if callback:
                callback(step, batch, current_predictions)
        return predictions

    async def _predict_one(self, item: ItemType, **kwargs) -> ReturnType:
        result = await self._predict_multiple([item], **kwargs)
        return result[0]

    async def _predict_multiple(
        self, items: List[ItemType], **kwargs
    ) -> List[ReturnType]:
        return [await self._predict_one(p, **kwargs) for p in items]

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


class TensorflowModel(Model[ItemType, ReturnType]):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.model_name = kwargs["model_asset"]
        output_tensor_mapping = kwargs.pop("output_tensor_mapping", {})
        self.output_tensor_mapping = output_tensor_mapping
        self.output_shapes = kwargs.get("output_shapes", {})
        self.output_dtypes = kwargs.pop(
            "output_dtypes", {name: np.float for name in output_tensor_mapping}
        )
        # sanity checks
        assert output_tensor_mapping.keys() == self.output_dtypes.keys()
        assert output_tensor_mapping.keys() == self.output_shapes.keys()

        # the GRPC stub
        self.grpc_stub = None

        # the session (for use with TF as an API)
        self.session = None
        self.output_names = None

        # TF serving parameters
        self.enable_tf_serving = self.service_settings.enable_tf_serving
        self.tf_serving_host = self.service_settings.tf_serving_host
        self.tf_serving_port = self.service_settings.tf_serving_port
        self.tf_serving_mode = self.service_settings.tf_serving_mode
        self.tf_serving_timeout_s = self.service_settings.tf_serving_timeout_s

        if self.enable_tf_serving and self.tf_serving_mode:
            wait_local_serving(
                self.model_name,
                self.tf_serving_host,
                self.tf_serving_port,
                self.tf_serving_mode,
                self.tf_serving_timeout_s,
            )
        else:
            saved_model = tf.saved_model.load(os.path.join(self.asset_path, "1"))
            self.tf_model_signature = saved_model.signatures[
                DEFAULT_SERVING_SIGNATURE_DEF_KEY
            ]
        self.aiohttp_session = None
        self.requests_session = None

    async def _predict_multiple(self, items, **kwargs):
        """A generic _predict_multiple that stacks and passes items to TensorFlow"""
        vects = {
            key: np.stack([item[key] for item in items], axis=0) for key in items[0]
        }
        return [await self._tensorflow_predict(vects)]

    async def _tensorflow_predict(
        self, vects: Dict[str, np.ndarray], grpc_dtype=None
    ) -> Dict[str, np.ndarray]:
        """
        a predict_multiple dispatching tf serving requests with the correct mode
        It takes a dictionary of numpy arrays of shape (Nitems, ?) and returns a
         dictionary for the same shape, indexed by self.output_keys
        """
        if self.enable_tf_serving and self.tf_serving_mode == "grpc":
            results = self._tensorflow_predict_grpc(vects, dtype=grpc_dtype)
        elif self.enable_tf_serving and self.tf_serving_mode == "rest":
            results = self._tensorflow_predict_rest(vects)
        elif self.enable_tf_serving and self.tf_serving_mode == "rest-async":
            results = await self._tensorflow_predict_rest_async(vects)
        else:
            results = self._tensorflow_predict_local(vects)
        return results

    def _tensorflow_predict_grpc(
        self, vects: Dict[str, np.ndarray], dtype=None
    ) -> Dict[str, np.ndarray]:
        request = PredictRequest()
        request.model_spec.name = self.model_name
        for key, vect in vects.items():
            request.inputs[key].CopyFrom(
                tf.compat.v1.make_tensor_proto(vect, dtype=dtype)
            )

        r, self.grpc_stub = make_serving_request(
            request,
            self.grpc_stub,
            self.model_name,
            self.tf_serving_host,
            self.tf_serving_port,
            self.tf_serving_mode,
            self.tf_serving_timeout_s,
        )
        return {
            output_key: np.array(
                r.outputs[output_key].ListFields()[-1][1],
                dtype=self.output_dtypes.get(output_key),
            ).reshape(vect.shape[0], -1)
            for output_key in self.output_tensor_mapping
        }

    def _tensorflow_predict_rest(
        self, vects: Dict[str, np.ndarray]
    ) -> Dict[str, np.ndarray]:
        if not self.requests_session:
            self.requests_session = requests.Session()
        response = self.requests_session.post(
            f"http://{self.tf_serving_host}:{self.tf_serving_port}"
            f"/v1/models/{self.model_name}:predict",
            data=json.dumps({"inputs": vects}),
        )
        if response.status_code != 200:
            raise TFServingError(
                f"TF Serving error [{response.reason}]: {response.text}"
            )
        response_json = response.json()
        outputs = response_json["outputs"]
        if not isinstance(outputs, dict):
            # with some (legacy) models, the output is the result, instead of a dict
            return {
                name: np.array(outputs, dtype=self.output_dtypes[name])
                for name in self.output_tensor_mapping
            }
        return {
            name: np.array(outputs[name], dtype=self.output_dtypes[name])
            for name in self.output_tensor_mapping
        }

    async def _tensorflow_predict_rest_async(
        self, vects: Dict[str, Any]
    ) -> Dict[str, np.ndarray]:
        if self.aiohttp_session is None:
            # aiohttp wants us to initialize the session in an event loop
            self.aiohttp_session = aiohttp.ClientSession()
        async with self.aiohttp_session.post(
            f"http://{self.tf_serving_host}:{self.tf_serving_port}"
            f"/v1/models/{self.model_name}:predict",
            data=json.dumps({"inputs": vects}),
        ) as response:
            if response.status != 200:
                raise TFServingError(
                    f"TF Serving error [{response.reason}]: {response.text}"
                )
            response_json = await response.json()
        outputs = response_json["outputs"]
        if not isinstance(outputs, dict):
            # with some (legacy) models, the output is the result, instead of a dict
            return {
                name: np.array(outputs, dtype=self.output_dtypes[name])
                for name in self.output_tensor_mapping
            }
        results = {
            name: np.array(outputs[name], dtype=self.output_dtypes[name])
            for name in self.output_tensor_mapping
        }
        return results

    def _tensorflow_predict_local(
        self, vects: Dict[str, np.ndarray]
    ) -> Dict[str, np.ndarray]:
        results = self.tf_model_signature(
            **{key: tf.convert_to_tensor(value) for key, value in vects.items()}
        )
        return {
            name: np.array(
                results[name],
                dtype=self.output_dtypes.get(name),
            )
            for name in self.output_tensor_mapping
        }

    def _generate_empty_prediction(self) -> Dict[str, Any]:
        """Function used to fill in values when rebuilding predictions with the mask"""
        return {
            name: np.zeros((1,) + self.output_shapes[name], self.output_dtypes[name])
            for name in self.output_tensor_mapping
        }

    def _rebuild_predictions_with_mask(
        self, mask: List[bool], predictions: Dict[str, np.ndarray]
    ) -> List[Dict[str, Any]]:
        """Merge the just-computed predictions with empty vectors for empty input items.
        Making sure everything is well-aligned"
        """
        i = 0
        results = []
        for mask_value in mask:
            if mask_value:
                results.append({name: value[i] for name, value in predictions.items()})
                i += 1
            else:
                results.append(self._generate_empty_prediction())
        return results


class DistantHTTPModelError(Exception):
    def __init__(self, status_code, reason, text):
        super().__init__(f"Service model error [{status_code} {reason}]: {text}")


def log_after_retry(retry_state):
    logger.info(
        "Retrying",
        fun=retry_state.fn.__name__,
        attempt_number=retry_state.attempt_number,
        wait_time=retry_state.outcome_timestamp - retry_state.start_time,
    )


def retriable_error(exception):
    return isinstance(
        exception, aiohttp.client_exceptions.ClientConnectorError
    ) or isinstance(exception, requests.exceptions.ConnectionError)


SERVICE_MODEL_RETRY_POLICY = {
    "wait": wait_random_exponential(multiplier=1, min=4, max=10),
    "stop": stop_after_attempt(5),
    "retry": retry_if_exception(retriable_error),
    "after": log_after_retry,
    "reraise": True,
}


class DistantHTTPModel(Model[ItemType, ReturnType]):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.endpoint = self.model_settings["endpoint"]
        self._async_mode = self.model_settings.get(
            "async_mode", self.service_settings.async_mode
        )
        self.aiohttp_session = None
        self.requests_session = None

    def _deserialize_asset(self):
        pass

    @retry(**SERVICE_MODEL_RETRY_POLICY)
    async def _predict_one_async(self, item):
        if self.aiohttp_session is None:
            # aiohttp wants us to initialize the session in an event loop
            self.aiohttp_session = aiohttp.ClientSession()
        async with self.aiohttp_session.post(
            self.endpoint,
            data=json.dumps(item),
        ) as response:
            if response.status != 200:
                raise DistantHTTPModelError(
                    response.status, response.reason, await response.text()
                )
            return await response.json()

    @retry(**SERVICE_MODEL_RETRY_POLICY)
    def _predict_one_sync(self, item):
        if not self.requests_session:
            self.requests_session = requests.Session()
        response = self.requests_session.post(
            self.endpoint,
            data=json.dumps(item),
        )
        if response.status_code != 200:
            raise DistantHTTPModelError(
                response.status_code, response.reason, response.text
            )
        return response.json()

    async def _predict_one(self, item):
        if self._async_mode is None:
            try:
                asyncio.get_event_loop()
                return await self._predict_one_async(item)
            except RuntimeError:
                return self._predict_one_sync(item)
        if self._async_mode:
            return await self._predict_one_async(item)
        return self._predict_one_sync(item)
