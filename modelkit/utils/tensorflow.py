import requests

from modelkit.log import logger

try:
    import grpc
    from tensorflow_serving.apis import prediction_service_pb2_grpc
    from tensorflow_serving.apis.get_model_metadata_pb2 import GetModelMetadataRequest
except ModuleNotFoundError:
    logger.info("Tensorflow serving is not installed")

from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)


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
    "wait": wait_random_exponential(multiplier=1, min=4, max=10),
    "stop": stop_after_attempt(5),
    "retry": retry_if_exception(retriable_error),
    "after": log_after_retry,
    "reraise": True,
}


def write_config(destination, models, verbose=False):
    with open(destination, "w") as f:
        f.write("model_config_list: {\n")
        for m, pth in models.items():
            f.write("    config: {\n")
            f.write(f'        name: "{m}", \n')
            f.write(f'        base_path: "{pth}",\n')
            f.write('        model_platform: "tensorflow"\n')
            f.write("    },\n")
        f.write("}")
    if verbose:
        with open(destination) as f:
            print(f.read())


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
            raise TFServingError(f"Error connecting to TF serving")
