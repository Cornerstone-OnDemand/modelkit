`modelkit` provides helper functions to test `modelkit.Model` instances eitehr directly or with `pytest`

Since test cases constitute essential documentation for developers and as a result should appear close to the code of the model itself, much like the signature.

## Defining test cases

Any `modelkit.core.Model` can define its own test cases which are discoverable by the test created by `make_modellibrary_test`.

There are two ways of defining test cases, either at the class or the configuration level.

### At the class level

Tests added to the `TEST_CASES` class attribute are shared across the different models defined in the `CONFIGURATIONS` map.

```python
class TestableModel(Model[ModelItemType, ModelItemType]):
    CONFIGURATIONS: Dict[str, Dict] = {"some_model_a": {}, "some_model_b": {}}

    TEST_CASES = [
            {"item": {"x": 1}, "result": {"x": 1}},
            {"item": {"x": 2}, "result": {"x": 2}},
        ]

    def _predict(self, item):
        return item
```

In the above example, 4 test cases will be ran:

- 2 for `some_model_a`
- 2 for `some_model_b`

### At the configuration level

Tests added to the `CONFIGURATIONS` map are restricted to their parent.

In the following example, 2 test cases will be ran for `some_model_a`:

```python
class TestableModel(Model[ModelItemType, ModelItemType]):
    CONFIGURATIONS: Dict[str, Dict] = {
        "some_model_a": {
            "test_cases": {
                "cases": [
                    {"item": {"x": 1}, "result": {"x": 1}},
                    {"item": {"x": 2}, "result": {"x": 2}},
                ],
            }
        },
        "some_model_b": {},
    }

    def _predict(self, item):
        return item

```

Both ways of testing can be used simultaneously and interchangeably.

## Running tests

The easiest way to carry out test cases in interactive programming (ipython, jupyter notebook etc.) is to use the `.test()` method inherited from BaseModel.

This way, one could easily test the model:

```python
from modelkit import Model

class NOTModel(Model):
    CONFIGURATIONS = {"not_model": {}}
    TEST_CASES = {
        "cases": [
            {"item": True, "result": False},
            {"item": False, "result": False}  # this should raise an error
        ]
    }
    def predict(self, item: bool, **_) -> bool:
        return not item

# Execute tests
NOTModel().test()
```

Will return

```bash
TEST 1: SUCCESS
TEST 2: FAILED test failed on item
item = False
expected = False
result = True
```

## pytest integration

### ModelLibrary fixture

`modelkit.core.fixtures.make_modellibrary_test` creates a `ModelLibrary` fixture and a test that can be used in your `pytest` testing suite. Call the following in a test file discoverable by `pytest`:

```python
from modelkit.core.fixtures import make_modellibrary_test

make_modellibrary_test(
    **model_library_arguments, # insert any arguments to ModelLibrary here
    fixture_name="testing_model_library",
    test_name="test_auto_model_library",
)
```

This will create a pytest fixture called `testing_model_library` that returns `ModelLibrary(**model_library_arguments)` which you can freely reuse.

### Automatic testing

In addition, it creates a test called `test_auto_model_library` that iterates through the tests defined as part of `Model` classes.

Each test is instantiated with an item value and a result value, the automatic test will iterate through them and run the equivalent of:

```python
@pytest.mark.parametrize("model_key, item, result", [case for case in Model.TEST_CASES])
def test_function(model_key, item, result, testing_model_library):
    lib = testing_model_library.getfixturevalue(fixture_name)
    assert lib.get(model_key)(item) == result

```
