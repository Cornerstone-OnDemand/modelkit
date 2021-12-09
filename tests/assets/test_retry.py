import copy

import botocore
import botocore.exceptions
import google.api_core
import pytest
import requests
from tenacity import retry, stop_after_attempt

from modelkit.assets.drivers.retry import RETRY_POLICY
from modelkit.assets.errors import ObjectDoesNotExistError


@pytest.mark.parametrize(
    "exception, exc_args",
    [
        (google.api_core.exceptions.GoogleAPIError, ()),
        (botocore.exceptions.ClientError, ({}, "operation_name")),
        (requests.exceptions.ChunkedEncodingError, ()),
    ],
)
def test_retry_policy(exception, exc_args):
    SHORT_RETRY_POLICY = copy.deepcopy(RETRY_POLICY)
    SHORT_RETRY_POLICY["stop"] = stop_after_attempt(2)
    k = 0

    @retry(**SHORT_RETRY_POLICY)
    def some_function():
        nonlocal k
        k += 1
        raise exception(*exc_args)

    with pytest.raises(exception):
        some_function()
    assert k == 2


def test_retry_policy_asset_error():
    SHORT_RETRY_POLICY = copy.deepcopy(RETRY_POLICY)
    SHORT_RETRY_POLICY["stop"] = stop_after_attempt(2)
    k = 0

    @retry(**SHORT_RETRY_POLICY)
    def some_function():
        nonlocal k
        k += 1
        raise ObjectDoesNotExistError("driver", "bucket", "object")

    with pytest.raises(ObjectDoesNotExistError):
        some_function()
    assert k == 1
