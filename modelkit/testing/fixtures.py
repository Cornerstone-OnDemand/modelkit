import dataclasses
import inspect
import os
import subprocess

import numpy as np
import pydantic
import pydantic.generics

from modelkit.core.library import ModelLibrary
from modelkit.core.model import Model
from modelkit.core.model_configuration import configure
from modelkit.core.models.tensorflow_model import connect_tf_serving
from modelkit.testing.reference import ReferenceJson
from modelkit.utils.tensorflow import deploy_tf_models


@dataclasses.dataclass
class JSONTestResult:
    fn: str


def modellibrary_auto_test(
    configuration=None,
    models=None,
    required_models=None,
    #  fixture name
    fixture_name="testing_model_library",
    test_name="testing_model_library",
    necessary_fixtures=None,
    fixture_scope="session",
    test_dir=".",
):
    import pytest

    #  fetch and tally all test cases within the models of the ModelLibrary
    test_cases = []
    configurations = configure(models=models, configuration=configuration)
    for model_key, model_configuration in configurations.items():
        if issubclass(model_configuration.model_type, Model):
            if required_models and model_key not in required_models:
                continue
            for (
                model_key,
                item,
                result,
                kwargs,
            ) in model_configuration.model_type._iterate_test_cases():
                test_cases.append((model_key, item, result, kwargs))

    #  create a parametrized test that runs through the different test cases
    @pytest.mark.parametrize("model_key, item, result, kwargs", test_cases)
    def test_function(model_key, item, result, kwargs, request):
        # get the above fixture by name
        svc = request.getfixturevalue(fixture_name)
        if isinstance(result, JSONTestResult):
            ref = ReferenceJson(os.path.join(test_dir, os.path.dirname(result.fn)))
            pred = svc.get(model_key)(item)
            if isinstance(pred, pydantic.BaseModel):
                pred = pred.dict()
            ref.assert_equal(os.path.basename(result.fn), pred)
        elif isinstance(result, np.ndarray):
            assert np.array_equal(svc.get(model_key)(item, **kwargs), result)
        else:
            assert svc.get(model_key)(item, **kwargs) == result

    # in order for the above functions to be collected by pytest, add them
    # to the caller's local variables under their desired names
    frame = inspect.currentframe().f_back
    frame.f_locals[test_name] = test_function


def modellibrary_fixture(
    # arguments passed directly to ModelLibrary
    settings=None,
    assetsmanager_settings=None,
    configuration=None,
    models=None,
    required_models=None,
    #  fixture name
    fixture_name="testing_model_library",
    necessary_fixtures=None,
    fixture_scope="session",
):
    import pytest

    #  create a named fixture with the ModelLibrary
    @pytest.fixture(name=fixture_name, scope=fixture_scope)
    def fixture_function(request):
        if necessary_fixtures:
            for fixture_name in necessary_fixtures:
                request.getfixturevalue(fixture_name)
        return ModelLibrary(
            settings=settings,
            assetsmanager_settings=assetsmanager_settings,
            configuration=configuration,
            models=models,
            required_models=required_models,
        )

    # in order for the above functions to be collected by pytest, add them
    # to the caller's local variables under their desired names
    frame = inspect.currentframe().f_back
    frame.f_locals[fixture_name] = fixture_function


def tf_serving_fixture(request, svc, deployment="docker"):
    cmd = [
        "--port=8500",
        "--rest_api_port=8501",
    ]

    deploy_tf_models(svc, "local-docker", config_name="testing")
    if deployment == "process":
        proc = subprocess.Popen(
            [
                "tensorflow_model_server",
                "--model_config_file="
                f"{os.environ['WORKING_DIR']}/{os.environ['STORAGE_PREFIX']}/"
                "testing.config",
            ]
            + cmd
        )

        def finalize():
            proc.terminate()

    else:
        # kill previous tfserving container (if any)
        subprocess.call(
            ["docker", "rm", "-f", "modelkit-tfserving-tests"],
            stderr=subprocess.DEVNULL,
        )
        # start tfserving as docker container
        tfserving_proc = subprocess.Popen(
            [
                "docker",
                "run",
                "--name",
                "modelkit-tfserving-tests",
                "--volume",
                f"{os.environ['WORKING_DIR']}:/config",
                "-p",
                "8500:8500",
                "-p",
                "8501:8501",
                "tensorflow/serving:2.4.0",
                "--model_config_file=/config/testing.config",
            ]
            + cmd
        )

        def finalize():
            subprocess.call(["docker", "kill", "modelkit-tfserving-tests"])
            tfserving_proc.terminate()

    request.addfinalizer(finalize)
    connect_tf_serving(
        next((x for x in svc.required_models)), "localhost", 8500, "grpc"
    )
