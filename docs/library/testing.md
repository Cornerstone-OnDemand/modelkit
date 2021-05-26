## Testing modelkit models

`modelkit` provides helper functions to test `modelkit.Model` instances with `pytest`.

The belief is that test cases for models constitute essential documentation for developers and as a result should appear close to the code of the model itself, much like item/result typing.

### ModelLibrary fixture and autotesting

`modelkit.core.fixtures.make_modellibrary_test` creates a `ModelLibrary` fixture and a test that can be used in your pytest testing suite. Call the following in a test file discoverable by pytest:

```python
from modelkit.core.fixtures import make_modellibrary_test

make_ModelLibrary_test(
    **prediction_service_arguments, # insert any arguments to ModelLibrary here
    fixture_name="testing_prediction_service",
    test_name="test_auto_prediction_service",
)
```

This will create a pytest fixture called `testing_prediction_service` that returns `ModelLibrary(**prediction_service_arguments)` which you can freely reuse.

In addition, it creates a test called `test_auto_prediction_service` that iterates through the tests defined as part of `Model` classes.


### Defining test cases

Any `modelkit.core.Model` can define its own test cases which are discoverable by the test created by `make_ModelLibrary_test`:

```python
class TestableModel(Model[ModelItemType, ModelItemType]):
    CONFIGURATIONS: Dict[str, Dict] = {"some_model": {}}

    TEST_CASES = {
        "cases": [
            {"item": {"x": 1}, "result": {"x": 1}},
            {"item": {"x": 2}, "result": {"x": 2}},
        ]
    }

    async def _predict_one(self, item):
        return item

```

Each test is instantiated with an item value and a result value, the automatic test will iterate through them and run the equivalent of:

```python
@pytest.mark.parametrize("model_key, item, result", [case for case in Model.TEST_CASES])
def test_function(model_key, item, result, testing_prediction_service):
    svc = testing_prediction_service.getfixturevalue(fixture_name)
    assert svc.get(model_key).predict(item) == result

```

## Troubleshooting

Here are a couple of issues that can occur when running the tests locally:

### Missing AWS credentials
If you see this message:
```
ClientError: An error occurred (ExpiredTokenException) when calling the GetParameter operation: The security token included in the request is expired`
```
Run the command `gimme-aws-creds` to update your AWS credentials and restart the tests.

### Missing GCS credentials
If you are not supposed to have access to GCS, you can ignore the GCS-related test by setting `ENABLE_GCS=False` in your environment variables.
NB: this won't be necessary once everything is migrated to AWS.
