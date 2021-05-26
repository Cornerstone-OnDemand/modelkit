import json
import os
from typing import Any, Dict, List

import aiohttp
import numpy as np
import requests
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)

from modelkit.core.model import Model
from modelkit.core.types import ItemType, ReturnType
from modelkit.log import logger

try:
    import tensorflow as tf
    from tensorflow.python.saved_model.signature_constants import (
        DEFAULT_SERVING_SIGNATURE_DEF_KEY,
    )

except ModuleNotFoundError:
    logger.info("tensorflow is not installed")

try:
    import grpc
    from tensorflow_serving.apis import prediction_service_pb2_grpc
    from tensorflow_serving.apis.get_model_metadata_pb2 import GetModelMetadataRequest
    from tensorflow_serving.apis.predict_pb2 import PredictRequest
except ModuleNotFoundError:
    logger.info("Tensorflow serving is not installed")


def safe_np_dump(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj.item()


class TensorflowModel(Model[ItemType, ReturnType]):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        output_tensor_mapping = kwargs.pop("output_tensor_mapping", {}) or kwargs[
            "model_settings"
        ].get("output_tensor_mapping")
        self.output_tensor_mapping = output_tensor_mapping
        self.output_shapes = kwargs.get("output_shapes", {}) or kwargs[
            "model_settings"
        ].get("output_shapes")
        self.output_dtypes = kwargs.pop(
            "output_dtypes", {name: np.float for name in output_tensor_mapping}
        ) or kwargs["model_settings"].get("output_dtypes")
        # sanity checks
        assert output_tensor_mapping.keys() == self.output_dtypes.keys()
        assert output_tensor_mapping.keys() == self.output_shapes.keys()

        # the GRPC stub
        self.grpc_stub = None

        # the session (for use with TF as an API)
        self.session = None
        self.output_names = None

        if self.service_settings.tf_serving.enable:
            self.grpc_stub = connect_tf_serving(
                self.configuration_key,
                self.service_settings.tf_serving.host,
                self.service_settings.tf_serving.port,
                self.service_settings.tf_serving.mode,
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
        prediction = await self._tensorflow_predict(vects)
        return [
            {key: prediction[key][k, ...] for key in self.output_shapes}
            for k in range(len(items))
        ]

    async def _tensorflow_predict(
        self, vects: Dict[str, np.ndarray], grpc_dtype=None
    ) -> Dict[str, np.ndarray]:
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
            if self.service_settings.tf_serving.mode == "rest-async":
                return await self._tensorflow_predict_rest_async(vects)
        return self._tensorflow_predict_local(vects)

    def _tensorflow_predict_grpc(
        self, vects: Dict[str, np.ndarray], dtype=None
    ) -> Dict[str, np.ndarray]:
        request = PredictRequest()
        request.model_spec.name = self.configuration_key
        for key, vect in vects.items():
            request.inputs[key].CopyFrom(
                tf.compat.v1.make_tensor_proto(vect, dtype=dtype)
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
        self, vects: Dict[str, np.ndarray]
    ) -> Dict[str, np.ndarray]:
        if not self.requests_session:
            self.requests_session = requests.Session()
        response = self.requests_session.post(
            f"http://{self.service_settings.tf_serving.host}:"
            f"{self.service_settings.tf_serving.port}"
            f"/v1/models/{self.configuration_key}:predict",
            data=json.dumps({"inputs": vects}, default=safe_np_dump),
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
            f"http://{self.service_settings.tf_serving.host}:"
            f"{self.service_settings.tf_serving.port}"
            f"/v1/models/{self.configuration_key}:predict",
            data=json.dumps({"inputs": vects}, default=safe_np_dump),
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


class TFServingError(Exception):
    pass


def log_after_retry(retry_state):
    logger.info(
        "Retrying TF serving connection",
        fun=retry_state.fn.__name__,
        attempt_number=retry_state.attempt_number,
        wait_time=retry_state.outcome_timestamp - retry_state.start_time,
    )


def retriable_error(exception):
    return isinstance(exception, Exception)


TF_SERVING_RETRY_POLICY = {
    "wait": wait_random_exponential(multiplier=1, min=4, max=20),
    "stop": stop_after_attempt(10),
    "retry": retry_if_exception(retriable_error),
    "after": log_after_retry,
    "reraise": True,
}


@retry(**TF_SERVING_RETRY_POLICY)
def connect_tf_serving(model_name, host, port, mode):
    logger.info(
        "Connecting to tensorflow serving",
        tf_serving_host=host,
        port=port,
        model_name=model_name,
        mode=mode,
    )
    if mode == "grpc":
        channel = grpc.insecure_channel(
            f"{host}:{port}", [("grpc.lb_policy_name", "round_robin")]
        )
        stub = prediction_service_pb2_grpc.PredictionServiceStub(channel)
        r = GetModelMetadataRequest()
        r.model_spec.name = model_name
        r.metadata_field.append("signature_def")
        answ = stub.GetModelMetadata(r, 1)
        version = answ.model_spec.version.value
        if version != 1:
            raise TFServingError(f"Bad model version: {version}!=1")
        return stub
    elif mode in {"rest", "rest-async"}:
        response = requests.get(f"http://{host}:{port}/v1/models/{model_name}")
        if response.status_code != 200:
            raise TFServingError("Error connecting to TF serving")
