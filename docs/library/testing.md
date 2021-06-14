## Testing modelkit models

`modelkit` provides helper functions to test `modelkit.Model` instances with `pytest`.

The belief is that test cases for models constitute essential documentation for developers and as a result should appear close to the code of the model itself, much like item/result typing.

### ModelLibrary fixture and autotesting

`modelkit.core.fixtures.make_modellibrary_test` creates a `ModelLibrary` fixture and a test that can be used in your pytest testing suite. Call the following in a test file discoverable by pytest:

```python
from modelkit.core.fixtures import make_modellibrary_test

make_modellibrary_test(
    **model_library_arguments, # insert any arguments to ModelLibrary here
    fixture_name="testing_model_library",
    test_name="test_auto_model_library",
)
```

This will create a pytest fixture called `testing_model_library` that returns `ModelLibrary(**model_library_arguments)` which you can freely reuse.

In addition, it creates a test called `test_auto_model_library` that iterates through the tests defined as part of `Model` classes.


### Defining test cases

Any `modelkit.core.Model` can define its own test cases which are discoverable by the test created by `make_modellibrary_test`:

```python
class TestableModel(Model[ModelItemType, ModelItemType]):
    CONFIGURATIONS: Dict[str, Dict] = {"some_model": {}}

    TEST_CASES = {
        "cases": [
            {"item": {"x": 1}, "result": {"x": 1}},
            {"item": {"x": 2}, "result": {"x": 2}},
        ]
    }

    def _predict(self, item):
        return item

```

Each test is instantiated with an item value and a result value, the automatic test will iterate through them and run the equivalent of:

```python
@pytest.mark.parametrize("model_key, item, result", [case for case in Model.TEST_CASES])
def test_function(model_key, item, result, testing_model_library):
    lib = testing_model_library.getfixturevalue(fixture_name)
    assert lib.get(model_key)(item) == result

```


The easiest way to carry out test cases in interactive programming (ipython, jupyter notebook etc.) is to use the `.test()` method inherited from BaseModel.

This way, one could easily test its brand new model:


```python
# Define your brand new model
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

```bash
TEST 1: SUCCESS
TEST 2: FAILED test failed on item
item = False                                                                                                                                                                                                            
expected = False                                                                                                                                                                                                        
result = True
```



