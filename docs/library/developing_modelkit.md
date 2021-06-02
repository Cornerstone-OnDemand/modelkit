## Models and assets

A `modelkit.Model` is a Python class implementing methods to deserialize assets (stored in the object store), and use them to make prediction.

Some quick `Model` facts:

- Models do not have to have an asset (text cleaning models)
- Models do not have to have a prediction method (they are then called `Asset`)
- Models can depend on other models and share objects in memory (in particular, they can share an `Asset`)
- Models can implement batched/vectorized logic
- Models can implement asynchronous logic and be called either way
- Models can implement the logic to fit themselves and generate the asset for prediction

### The `Model` class

`modelkit` models are subclasses of the `modelkit.core.model.Model` class.

The prediction logic is implemented in an asynchronous `_predict` method that takes a single argument `item`. This represents a single item, which is usually a json serializable dict (with maybe numpy arrays). In fact, Models implement `_predict` or `_predict_batch` (both async) methods, and `Model` appropriately chooses between them and batches.

The asset loading logic is implemented in a `_load` method that is run after the `Model` is instantiated, and can load the asset specified in the `Model`'s configuration. For more on this see Lazy Mode.

### The simplest `Model` class

This simple model class will always return `"something"`:

```python
from modelkit.core.model import Model

class SimpleModel(Model):
    async def _predict(self, item) -> str:
        return "something"
```

It can be loaded to make "predictions" as so:

```python
m = SimpleModel()
m({}) # returns "YOLO les simpsons"
```

### Model configurations

As models become more complicated they are attached to different assets or other models. We will need to instanciate them through the `ModelLibrary` object which will take care of all this for us.

To do so, we have to _configure_ our model: give it a name and dependencies.

Models are made available to clients using `modelkit` by specifying them using the `CONFIGURATIONS` class attribute:

```python
class SimpleModel(Model):
    CONFIGURATIONS = {
        "simple": {}
    }
    async def _predict(self, item):
        return "something"
```

!!! important
    You have to `async def` when implementing `_predict` and `_predict_batch`, even if the function is synchronous.

Right now, we have only given it a name `"simple"` which makes the model available to other models via the `ModelLibrary`.

The rest of the configuration is empty but we will add to it at the next section.

Assuming that `SimpleModel` is defined in `my_module.my_models`, it is now accessible via:

```python
from modelkit.core import ModelLibrary
import my_module.my_models

p = ModelLibrary(models=my_module.my_models)
m = p.get("simple")
```

See [Organization](organizing.md) for more information on how to organize your models.

### Model settings

The simplest configuration options are `model_settings`:

```python
from modelkit.core.model import Model

class SimpleModel(Model):
    CONFIGURATIONS = {
        "simple": {"model_settings": {"value" : "something"}},
        "simple2": {"model_settings": {"value" : "something2"}}
    }
    async def _predict(self, item):
        return self.model_settings["value"]
```

Now, there are two versions of the model available, `simple` and `simple2`:

```python
from modelkit.core import ModelLibrary

p = ModelLibrary(models=YOLOModel)
m = p.get("simple")
print(m({}))
m2 = p.get("simple2")
print(m2({}))
```

It will print both `"something"` and `"something2"`.

## Model assets and dependencies

The usefulness of modelkit `Model`s and their configuration is more apparent when they depend on assets or other models.

### Model assets

A model can implement a `_load` method that loads information from an asset stored locally, or retrieved from an object store at run time. It may contain files, folders, parameters, optimized data structures, or anything really.

The model asset is specified in the `CONFIGURATIONS` with `asset=asset_name:version`, following `storage.AssetsManager` conventions (see [Assets](../assets/assets.md)).

When the `_load` method is called, the object will have an `asset_path` attribute that points to the path of the asset locally. This is then used to load the relevant information from the asset file(s).

### Model with asset example

Adding the key to the model's configuration:

```python
class ModelWithAsset(Model):
    CONFIGURATIONS = {
        "model_with_asset": {"asset": "test/yolo:1"}
    }
```

Will cause the `ModelLibrary` to download `gs://bucket/assets/test/1/yolo` locally to the assets folder folder (which storage provider and bucket is used depends on your configuration), and set the `Model.asset_path` attribute accordingly.

It is up to the user to define the deserialization logic:

```python
class ModelWithAsset(Model):
    def _load(self):
        # For example, here, the asset is a BZ2 compressed JSON file
        with bz2.BZ2File(self.asset_path, "rb") as f:
            self.data_structure = pickle.load(f) # loads {"response": "YOLO les simpsons"}

    async def _predict(self, item: Dict[str, str], **kwargs) -> float:
        return self.data_structure["response"] # returns "YOLO les simpsons"
```

!!! note
    Assets retrieval is handled by `modelkit`, and it is guaranteed that they be present when `_load` is called, even in lazy mode. However, it is not true when `__init__` is called. In general, it is not a good idea to subclass `__init__`.

### Model dependencies

In addition, `modelkit` models are **composable**.

That is, a `Model` can depend on other `Model`s, and exploit their attributes and predictions.

For example your can set your model's configuration to have access to two other `Model` objects:

```python
class SomeModel(Model):
    CONFIGURATIONS = {
        "some_model": {
            "model_dependencies": {
                "sentence_piece_cleaner",
                "sentence_piece_vectorizer"
            }
        }
    }
```

The `ModelLibrary` ensures that whenever `_load` or the `_predict_*` function are called, these models are loaded and present in the `model_dependencies` dictionary:

```python
async def _predict(self, item):
    cleaned = self.models_dependencies["sentence_piece_cleaner"](item["text"])
    ...

```

In addition, it is possible to rename dependencies on the fly by providing a mapping to `model_dependencies`:

```python
class SomeModel(Model):
    CONFIGURATIONS = {
        "some_model": {
            "model_dependencies": {
                "cleaner": "sentence_piece_cleaner",
            }
        },
        "some_model_2": {
            "model_dependencies": {
                "cleaner": "sentence_piece_cleaner_2
            }
        }
    }
```

In this case, the instantiated `SomeModel.model_dependencies["cleaner"]` will point to `sentence_piece_cleaner` in one configuration and to `sentence_piece_cleaner_2` in the other.

### Model attributes

`Model` have several attributes set by the `ModelLibrary` when they are initialized:

- `asset_path` the path to the asset set in the `Model`'s configuration
- `configuration_key` the key of the model's configuration
- `model_dependencies` a dictionary of `Model` dependencies
- `model_settings` the `model_settings` as passed at initialization
- `service_settings` the settings of the `ModelLibrary` that created the model

And a set of attributes always present:

- `model_classname` the name of the `Model`'s subclass
- `batch_size` the batch size for the model: if `_predict_batch` is implemented it will always get batches of this size (defaults to 64)

## Model typing

It is also possible to provide types for a `Model` subclass, such that linters and callers know exactly which `item` type is expected, and what the result of a `Model` call look like.

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

```
m = SomeTypedModel()
x : int = m("ok")
y : List[int] = m(["ok", "boomer"])
z : int = m(1) # would lead to a typing error with typecheckers (e.g. mypy)
```

### Runtime type validation

In addition, whenever the model's `predict` method is called, the type of the item is validated against the provided type and raises an error if the validation fails:

- `modelkit.core.model.ItemValidationException` if the item fails to validate
- `modelkit.core.model.ReturnValueValidationException` if the return value of the predict fails to validate

### Marshalling of item/return values

It is possible to specify a `pydantic.BaseModel` subtype as a type argument for `Model` classes. This will actually _change the structure of the data_ that is fed into to the `_predict_[one|multiple]` method.

That is, even though the `predict` is called with dictionnaries, the `_predict_[one|multiple]` method is guaranteed to be called with an instance of the defined `pydantic` structure for item, and similarly for the output. For example:

```python
class ItemModel(pydantic.BaseModel):
    x: int

class ReturnModel(pydantic.BaseModel):
    x: int

class SomeValidatedModel(Model[ItemModel, ReturnModel]):
    async def _predict(self, item):
        # item is guaranteed to be an instance of `ItemModel` even if we feed a dictionary item
        return {"x": item.x}

m = SomeValidatedModel()
# although we return a dict from the _predict method, return value
# is turned into a `ReturnModel` instance.
y : ReturnModel = m({"x": 1})
# which also works with lists of items
y : List[ReturnModel] = m([{"x": 1}, {"x": 2}])
```

## Batching and vectorization


`Model` can easily deal with a single item or multiple items in the inputs:
```python

class Identity(Model)
    async def _predict(self, item):
        return item
    
m = Identity()
m({}) # == {}
m([{}, {"hello": "world"}]) == [{}, {"hello": "world"}]
```

It is sometimes interesting to implement batched or vectorized logic, to treat
batches of inputs at once. In this case, one can override `_predict_batch` instead of `_predict`:

```python

class IdentityBatched(Model)
    async def _predict(self, items):
        return items
    
m_batched = IdentityBatched()
```

Requesting model predictions will lead to the exact same result:

```python
m_batched({}) # == {}
m_batched([{}, {"hello": "world"}]) == [{}, {"hello": "world"}]
```

### Batch size

When `_predict_muliple` is overridden, the `Model` will call it with lists of items. 
The length of the list can be controled by the `batch_size`, either at call time:

```python
m_batched([{}, {"hello": "world"}], batch_size=2) 
```

or set in the model configuration

```python
class IdentityBatched(Model):
    CONFIGURATIONS = {
        "some_model": {
            "model_settings": {
                "batch_size": 32
            }
        }
    }
    async def _predict(self, items):
        return items
```

## `Asset` class

It is sometimes useful for a given asset in memory to serve many different `Model` objects. It is possibly by using the `model_dependencies` to point to a parent `Model` that is the only one to load the asset via `_load`.

In this case, we may not want the parent asset-bearing `Model` object to implement `predict` at all.

This is what an `modelkit.core.model.Asset` is.

!!! note
    In fact, it is defined the other way around: `Model`s are `Asset`s with a predict function, and thus `Model` inherits from `Asset`.

!!! note
    There are two ways to use a data asset in a `Model`: either load it directly via its configuration and the `_load`, or package it in an `Asset` and use the deserialized object via model dependencies.

### Asset file override for debugging

There are two ways to override the asset file for a model:

You can force to use a local or a remote (e.g. on object store) file for a model by setting an environment variable: `modelkit_{}_FILE".format(model_asset.upper())`.

It is also possible to set this programmatically:

```python
service = ModelLibrary(required_models =
        {
            "my_favorite_model":{
                "asset_path": "/path/to/asset"
            }
        }
    )
```

## `DistantHTTPModel`

Sometimes models will simply need to call another microservice, in this case `DistantHTTPModel` are the way to go. They are instantiated with a POST endpoint URL.

```python
class SomeDistantHTTPModel(DistantHTTPModel):
    CONFIGURATIONS = {
        "some_model": {
            "model_settings": {
                "endpoint": "http://127.0.0.1:8000/api/path/endpoint",
                "async_mode": False
            }
        }
    }
```

When `predict[_async]` is called, an asynchronous request is made to the `http://127.0.0.1:8000/api/path/endpoint` with the complete input item serialized in the body and the response of the server is returned.

This model supports asynchronous and synchronous requests to the distance model (using either `requests` or `aiohttp`). If the model setting `async_mode` is unset, each predict call will determine whether it is called in an asychronous environment and choose the best option. If it is set, then all calls will use the same strategy.

In addition, it is possible to set this behavior at the level of the `ModelLibrary` by either setting the `async_mode` setting in the `LibrarySettings` or by setting the environment variable `modelkit_ASYNC_MODE`.
