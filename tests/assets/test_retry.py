import copy

import botocore
import botocore.exceptions
import google.api_core
import pytest
import requests
from tenacity import retry, stop_after_attempt

from modelkit.assets.drivers.retry import retry_policy
from modelkit.assets.errors import ObjectDoesNotExistError


@pytest.mark.parametrize(
    "exception, exc_args, policy",
    [
        (
            google.api_core.exceptions.GoogleAPIError,
            (),
            retry_policy(google.api_core.exceptions.GoogleAPIError),
        ),
        (
            botocore.exceptions.ClientError,
            ({}, "operation_name"),
            retry_policy(botocore.exceptions.ClientError),
        ),
        (requests.exceptions.ChunkedEncodingError, (), retry_policy(None)),
    ],
)
def test_retry_policy(exception, exc_args, policy):
    SHORT_RETRY_POLICY = copy.deepcopy(policy)
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
    SHORT_RETRY_POLICY = copy.deepcopy(retry_policy(None))
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
