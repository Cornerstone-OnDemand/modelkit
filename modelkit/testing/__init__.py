from modelkit.testing.fixtures import (
    JSONTestResult,
    modellibrary_auto_test,
    modellibrary_fixture,
)
from modelkit.testing.reference import ReferenceJson, ReferenceText

try:
    from modelkit.testing.tf_serving import tf_serving_fixture
except NameError:
    # This occurs because type annotations in
    # modelkit.core.models.tensorflow_model will raise
    # `NameError: name 'prediction_service_pb2_grpc' is not defined`
    # when tensorflow-serving-api is not installed
    pass

# flake8: noqa: F401
