import abc
import json
import os
from typing import Any, Dict, List, Optional, Tuple, Type

import aiohttp
import requests
from structlog import get_logger
from tenacity import (
    Retrying,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)

from modelkit.core.model import AsyncModel, Model
from modelkit.core.types import ItemType, ReturnType
from modelkit.utils.serialization import safe_np_dump

logger = get_logger(__name__)

try:
    import tensorflow as tf
    from tensorflow.python.saved_model.signature_constants import (
        DEFAULT_SERVING_SIGNATURE_DEF_KEY,
    )

    has_tensorflow = True
except ModuleNotFoundError:  # pragma: no cover
    has_tensorflow = False
    logger.info("tensorflow is not installed")

try:
    import grpc
    from tensorflow_serving.apis import prediction_service_pb2_grpc
    from tensorflow_serving.apis.get_model_metadata_pb2 import GetModelMetadataRequest
    from tensorflow_serving.apis.predict_pb2 import PredictRequest

except ModuleNotFoundError:  # pragma: no cover
    logger.info("Tensorflow serving is not installed")


try:
    import numpy as np

except ModuleNotFoundError:  # pragma: no cover
    logger.info("numpy is not installed")


class TensorflowModelMixin(abc.ABC):
    output_shapes: Dict[str, Tuple]
    output_dtypes: Dict[str, Type]
    output_tensor_mapping: Dict[str, str]

    def __init__(self, *args, **kwargs):
        if not has_tensorflow:
            raise ImportError(
                "Tensorflow is not installed, instal modelkit[tensorflow]."
            )

    def _is_empty(self, item) -> bool:
        return False

    def _generate_empty_prediction(self) -> Dict[str, Any]:
        """Function used to fill in values when rebuilding predictions with the mask"""
        return {
            name: np.zeros((1,) + self.output_shapes[name], self.output_dtypes[name])
            for name in self.output_tensor_mapping
        }

    def _rebuild_predictions_with_mask(
        self, mask: List[bool], predictions: Dict[str, "np.ndarray"]
    ) -> List[Dict[str, Any]]:
        """Merge the just-computed predictions with empty vectors for empty input items.
        Making sure everything is well-aligned"
        """
        i = 0
        results = []
        for mask_value in mask:
            if mask_value:
                results.append(self._generate_empty_prediction())
            else:
                results.append(
                    {name: predictions[name][i] for name in self.output_tensor_mapping}
                )
                i += 1
        return results


class TensorflowModel(Model[ItemType, ReturnType], TensorflowModelMixin):
    def __init__(
        self,
        output_tensor_mapping: Optional[Dict[str, str]] = None,
        output_shapes: Optional[Dict[str, Tuple]] = None,
        output_dtypes: Optional[Dict[str, "np.dtype"]] = None,
        tf_model_name: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.output_tensor_mapping = output_tensor_mapping or kwargs[
            "model_settings"
        ].get("output_tensor_mapping")
        self.output_shapes = output_shapes or kwargs["model_settings"].get(
            "output_shapes"
        )
        self.output_dtypes = (
            output_dtypes  # type: ignore
            or kwargs["model_settings"].get("output_dtypes")
            or {name: float for name in self.output_tensor_mapping}
        )
        # sanity checks
        assert self.output_tensor_mapping.keys() == self.output_dtypes.keys()
        assert self.output_tensor_mapping.keys() == self.output_shapes.keys()

        self.tf_model_name = (
            tf_model_name
            or kwargs.get("model_settings", {}).get("tf_model_name")
            or self.configuration_key
        )

        # the GRPC stub
        self.grpc_stub: Optional[
            prediction_service_pb2_grpc.PredictionServiceStub
        ] = None

        # the session (for use with TF as an API)
        self.session = None
        self.output_names = None

        if self.service_settings.tf_serving.enable:
            self.grpc_stub = connect_tf_serving(
                self.tf_model_name,
                self.service_settings.tf_serving.host,
                self.service_settings.tf_serving.port,
                self.service_settings.tf_serving.mode,
            )
        else:
            self.saved_model = tf.saved_model.load(os.path.join(self.asset_path, "1"))
            self.tf_model_signature = self.saved_model.signatures[
                DEFAULT_SERVING_SIGNATURE_DEF_KEY
            ]
        self.requests_session: Optional[requests.Session] = None

    def _predict_batch(self, items, **kwargs):
        """A generic _predict_batch that stacks and passes items to TensorFlow"""
        mask = [self._is_empty(item) for item in items]
        if all(mask):
            return self._rebuild_predictions_with_mask(mask, {})
        vects = {
            key: np.stack(
                [item[key] for item, mask in zip(items, mask) if not mask], axis=0
            )
            for key in items[0]
        }
        predictions = self._tensorflow_predict(vects)
        return self._rebuild_predictions_with_mask(mask, predictions)

    def _tensorflow_predict(
        self, vects: Dict[str, "np.ndarray"], grpc_dtype=None
    ) -> Dict[str, "np.ndarray"]:
        """
        a predict_multiple dispatching tf serving requests with the correct mode
        It takes a dictionary of numpy arrays of shape (Nitems, ?) and returns a
         dictionary for the same shape, indexed by self.output_keys
        """
        if self.service_settings.tf_serving.enable:
            if self.service_settings.tf_serving.mode == "grpc":
                return self._tensorflow_predict_grpc(vects, dtype=grpc_dtype)
            if self.service_settings.tf_serving.mode == "rest":
                return self._tensorflow_predict_rest(vects)
        return self._tensorflow_predict_local(vects)

    def _tensorflow_predict_grpc(
        self, vects: Dict[str, "np.ndarray"], dtype=None
    ) -> Dict[str, "np.ndarray"]:
        request = PredictRequest()
        request.model_spec.name = self.tf_model_name
        for key, vect in vects.items():
            request.inputs[key].CopyFrom(
                tf.compat.v1.make_tensor_proto(vect, dtype=dtype)
            )
        if not self.grpc_stub:
            self.grpc_stub = connect_tf_serving_grpc(
                self.tf_model_name,
                self.service_settings.tf_serving.host,
                self.service_settings.tf_serving.port,
            )

        r = self.grpc_stub.Predict(request, 1)

        return {
            output_key: np.array(
                r.outputs[output_key].ListFields()[-1][1],
                dtype=self.output_dtypes.get(output_key),
            ).reshape((vect.shape[0],) + self.output_shapes[output_key])
            for output_key in self.output_tensor_mapping
        }

    def _tensorflow_predict_rest(
        self, vects: Dict[str, "np.ndarray"]
    ) -> Dict[str, "np.ndarray"]:
        if not self.requests_session:
            self.requests_session = requests.Session()
        response = self.requests_session.post(
            f"http://{self.service_settings.tf_serving.host}:"
            f"{self.service_settings.tf_serving.port}"
            f"/v1/models/{self.tf_model_name}:predict",
            data=json.dumps({"inputs": vects}, default=safe_np_dump),
        )
        if response.status_code != 200:  # pragma: no cover
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

    def _tensorflow_predict_local(
        self, vects: Dict[str, "np.ndarray"]
    ) -> Dict[str, "np.ndarray"]:
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

    def close(self):
        if self.requests_session:
            return self.requests_session.close()


class AsyncTensorflowModel(AsyncModel[ItemType, ReturnType], TensorflowModelMixin):
    def __init__(
        self,
        output_tensor_mapping: Optional[Dict[str, str]] = None,
        output_shapes: Optional[Dict[str, Tuple]] = None,
        output_dtypes: Optional[Dict[str, "np.dtype"]] = None,
        tf_model_name: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.output_tensor_mapping = output_tensor_mapping or kwargs[
            "model_settings"
        ].get("output_tensor_mapping")
        self.output_shapes = output_shapes or kwargs["model_settings"].get(
            "output_shapes"
        )
        self.output_dtypes = (
            output_dtypes  # type: ignore
            or kwargs["model_settings"].get("output_dtypes")
            or {name: float for name in self.output_tensor_mapping}
        )
        # sanity checks
        assert self.output_tensor_mapping.keys() == self.output_dtypes.keys()
        assert self.output_tensor_mapping.keys() == self.output_shapes.keys()

        self.tf_model_name = (
            tf_model_name
            or kwargs.get("model_settings", {}).get("tf_model_name")
            or self.configuration_key
        )

        connect_tf_serving(
            self.tf_model_name,
            self.service_settings.tf_serving.host,
            self.service_settings.tf_serving.port,
            self.service_settings.tf_serving.mode,
        )
        self.aiohttp_session: Optional[aiohttp.ClientSession] = None

    async def _predict_batch(self, items, **kwargs):
        """A generic _predict_batch that stacks and passes items to TensorFlow"""
        mask = [self._is_empty(item) for item in items]
        if all(mask):
            return self._rebuild_predictions_with_mask(mask, {})
        vects = {
            key: np.stack(
                [item[key] for item, mask in zip(items, mask) if not mask], axis=0
            )
            for key in items[0]
        }
        predictions = await self._tensorflow_predict(vects)
        return self._rebuild_predictions_with_mask(mask, predictions)

    async def _tensorflow_predict(
        self, vects: Dict[str, "np.ndarray"]
    ) -> Dict[str, "np.ndarray"]:
        if self.aiohttp_session is None:
            # aiohttp wants us to initialize the session in an event loop
            self.aiohttp_session = aiohttp.ClientSession()
        async with self.aiohttp_session.post(
            f"http://{self.service_settings.tf_serving.host}:"
            f"{self.service_settings.tf_serving.port}"
            f"/v1/models/{self.tf_model_name}:predict",
            data=json.dumps({"inputs": vects}, default=safe_np_dump),
        ) as response:
            if response.status != 200:  # pragma: no cover
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
        return {
            name: np.array(outputs[name], dtype=self.output_dtypes[name])
            for name in self.output_tensor_mapping
        }

    async def close(self):
        if self.aiohttp_session:
            return await self.aiohttp_session.close()


class TFServingError(Exception):
    pass


def log_after_retry(name):
    return lambda retry_state: logger.info(
        "Retrying TF serving connection",
        name=name,
        attempt_number=retry_state.attempt_number,
        wait_time=retry_state.outcome_timestamp - retry_state.start_time,
    )


def retriable_error(exception):
    return isinstance(exception, Exception)


def tf_serving_retry_policy(name):
    return {
        "wait": wait_random_exponential(
            multiplier=1,
            min=4,
            max=20,
        ),
        "stop": stop_after_attempt(
            int(os.environ.get("MODELKIT_TF_SERVING_ATTEMPTS", 10))
        ),
        "retry": retry_if_exception(retriable_error),
        "after": log_after_retry(name),
        "reraise": True,
    }


def connect_tf_serving_grpc(
    model_name, host, port
) -> "prediction_service_pb2_grpc.PredictionServiceStub":

    try:
        for attempt in Retrying(**tf_serving_retry_policy("tf-serving-grpc")):
            with attempt:
                channel = grpc.insecure_channel(
                    f"{host}:{port}", [("grpc.lb_policy_name", "round_robin")]
                )
                stub = prediction_service_pb2_grpc.PredictionServiceStub(channel)
                r = GetModelMetadataRequest()
                r.model_spec.name = model_name
                r.metadata_field.append("signature_def")
                answ = stub.GetModelMetadata(r, 1)
                version = answ.model_spec.version.value
                if version != 1:  # pragma: no cover
                    raise TFServingError(f"Bad model version: {version}!=1")
                return stub
    except grpc.RpcError:
        logger.error("Error connecting to TF serving")
        raise


def connect_tf_serving_rest(model_name, host, port) -> None:
    try:
        for attempt in Retrying(**tf_serving_retry_policy("tf-serving-rest")):
            with attempt:
                response = requests.get(f"http://{host}:{port}/v1/models/{model_name}")
                if response.status_code != 200:  # pragma: no cover
                    raise TFServingError("Error connecting to TF serving")
    except requests.exceptions.ConnectionError:
        logger.error("Error connecting to TF serving")
        raise


def connect_tf_serving(model_name, host, port, mode):
    logger.info(
        "Connecting to tensorflow serving",
        tf_serving_host=host,
        port=port,
        model_name=model_name,
        mode=mode,
    )
    if mode == "grpc":
        return connect_tf_serving_grpc(model_name, host, port)
    elif mode == "rest":
        return connect_tf_serving_rest(model_name, host, port)
