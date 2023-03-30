
## `DistantHTTPModel`

Sometimes models will simply need to call another microservice, in this case `DistantHTTPModel` are the way to go. They are instantiated with a POST endpoint URL.

```python
from modelkit.core.models.distant_model import DistantHTTPModel

class SomeDistantHTTPModel(DistantHTTPModel):
    CONFIGURATIONS = {
        "some_model": {
            "model_settings": {
                "endpoint": "http://127.0.0.1:8000/api/path/endpoint",
            }
        }
    }
```

Note that the params of your endpoint should be specified under `endpoint_params` in your `model_settings`.
When `predict` is called, a request is made to the `http://127.0.0.1:8000/api/path/endpoint` with the complete input item serialized in the body and the response of the server is returned.


In addition, it is possible to set this behavior at the level of the `ModelLibrary` by either setting the `async_mode` setting in the `LibrarySettings` or by setting the environment variable `modelkit_ASYNC_MODE`.

## async support

The `AsyncDistantHTTPModel` provides a base class with the same interface as `DistantHTTPModel` but supports distant requests with `aiohttp`.


## batch support

The `DistantHTTPBatchModel` provides a base class with a similair interface as `DistantHTTPModel` except that it implements the `predict_batch` method enabling you to make optimized requests to a batch endpoint. Note that the endpoint must accept a list of items as input.

## Closing connections

To close connections, you can do it at the level of the `ModelLibrary` either calling:

- `ModelLibrary.close()` in a synchronous context
- `await ModelLibrary.aclose()` in an asynchronous context

This will iterate through all existing models and call `close` (which is either sync or async according to the model type).
