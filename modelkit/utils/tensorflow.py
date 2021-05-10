import random
import time

import requests

from modelkit.log import logger

try:
    import grpc
    from tensorflow_serving.apis import prediction_service_pb2_grpc
    from tensorflow_serving.apis.get_model_metadata_pb2 import GetModelMetadataRequest
except ModuleNotFoundError:
    logger.info("tensorflow is not installed")


class TFServingError(Exception):
    pass


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


def wait_local_serving(model_asset, host, port, mode, timeout):
    logger.info(
        "Connecting to tensorflow serving",
        tf_serving_host=host,
        port=port,
        model_asset=model_asset,
        mode=mode,
    )

    start_time = time.monotonic()
    while True:
        try:
            if mode == "grpc":
                return try_local_serving_grpc(model_asset, host, port)
            elif mode in {"rest", "rest-async"}:
                return try_local_serving_restful(model_asset, host, port)
        except Exception as e:
            duration = time.monotonic() - start_time
            logger.info(
                "Waiting for tensorflow server",
                model_asset=model_asset,
                duration=duration,
                mode=mode,
                error=e,
            )
            if duration > timeout:
                logger.error(
                    "Fail to launch tensorflow server",
                    model_asset=model_asset,
                    duration=duration,
                    exception=e,
                    mode=mode,
                )
                raise TFServingError("Cannot get working tensorflow server in time")
            time.sleep(1)


def try_local_serving_grpc(model_name, host, port):
    channel = grpc.insecure_channel(
        f"{host}:{port}", [("grpc.lb_policy_name", "round_robin")]
    )
    stub = prediction_service_pb2_grpc.ModelLibraryStub(channel)
    r = GetModelMetadataRequest()
    r.model_spec.name = model_name
    r.metadata_field.append("signature_def")
    answ = stub.GetModelMetadata(r, 1)
    version = answ.model_spec.version.value
    if version != 1:
        raise ValueError(f"Bad model version: {version}!=1")
    return stub


def try_local_serving_restful(model_name, host, port):
    response = requests.get(f"http://{host}:{port}/v1/models/{model_name}")
    assert response.status_code == 200
    return response.json()


def stub_need_connection(stub):
    if stub is None:
        return True
    else:
        # this allow to refresh the connections regularly and thus to take
        # into account new pods arriving
        # It gives less control than monitoring request counts or connection
        # duration, but is a lot easier to introduce
        # In current benchmark, performing 10k queries takes ~7s, so with
        # this number we may assume to reconnect every few seconds in case
        # of high load. In case of low load, we do not really care of load
        # balancing
        return random.randint(0, 10000) == 0


def make_serving_request(request, stub, model_asset, host, port, mode, timeout):
    for i in range(5):
        if stub_need_connection(stub):
            stub = wait_local_serving(model_asset, host, port, mode, timeout)
        try:
            r = stub.Predict(request, 1)
            return r, stub
        except Exception as e:
            logger.warning(
                "Request failed, retrying",
                attempt=i + 1,
                exception=e,
                model_asset=model_asset,
            )
            stub = None
    raise Exception(f"Unable to perform tensorflow serving request for {model_asset}")
