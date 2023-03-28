## Model typing

It is also possible to provide types for a `Model` subclass, such that linters and callers know exactly which `item` type is expected, and what the result of a `Model` call looks like.

Types are specified when instantiating the `Model` class:

```python
# This model takes `str` items and always returns `int` values
class SomeTypedModel(Model[str, int]):
    def _predict(self, item):
        return len(item)
```

### Static type checking

Setting `Model` types allows static type checkers to fail if the expected return value of calls to `predict` have the wrong types.

Consider the above model:

```python
m = SomeTypedModel()
x : int = m("ok")
y : List[int] = m(["ok", "boomer"])
z : int = m(1) # would lead to a typing error with typecheckers (e.g. mypy)
```

## Runtime type validation

In addition, whenever the model's `predict` method is called, the type of the item is validated against the provided type and raises an error if the validation fails:

- `modelkit.core.model.ItemValidationException` if the item fails to validate
- `modelkit.core.model.ReturnValueValidationException` if the return value of the predict fails to validate

### Marshalling of item/return values

It is possible to specify a `pydantic.BaseModel` subtype as a type argument for `Model` classes. This will actually _change the structure of the data_ that is fed into to the `_predict` method. For example:


```python
class ItemModel(pydantic.BaseModel):
    x: int

class ReturnModel(pydantic.BaseModel):
    x: int

class SomeValidatedModel(Model[ItemModel, ReturnModel]):
    def _predict(self, item):
        # item is guaranteed to be an instance of `ItemModel` even if we feed a dictionary item
        result = {"x": item.x}
        # We can either return a dictionary
        return result
        # or return the pydantic structure
        # return ReturnModel(x = item.x)

m = SomeValidatedModel()
# although we return a dict from the _predict method, return value
# is turned into a `ReturnModel` instance.
y : ReturnModel = m({"x": 1})
```

This also works with list of items

```python
class SomeValidatedModelBatch(Model[ItemModel, ReturnModel]):
    def _predict_batch(self, items):
        return [{"x": item.x} for item in items]

m = SomeValidatedModelBatch()
y : List[ReturnModel] = m.predict_batch(items=[{"x": 1}, {"x": 2}])
```

!!! note

    Note that, although we call `predict` with a dictionary, `_predict` will see pydantic structures. Importantly, this means that attributes now need to be refered to with _natural naming_: `item.x` instead of `item["x"]`

### Disabling validation

`pydantic` validation can take some time, and in some cases the validation may end up taking much more time than the prediction itself.

This occurs generally when:

- a `Model`'s payload is large (contains long lists of objects to validate)
- a `Model`'s prediction is very simple

To avoid the validation overhead, especially in production scenarios, it is possible to ask `modelkit` to [create models without validation](https://pydantic-docs.helpmanual.io/usage/models/#creating-models-without-validation), which will be faster in general. This also still creates `pydantic` structure and therefore will not break the natural naming inside the `predict` function.
