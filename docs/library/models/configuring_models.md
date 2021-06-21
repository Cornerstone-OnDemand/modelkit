As models become more complicated they are attached to different assets or other models. We will need to instanciate them through the `ModelLibrary` object which will take care of all this for us.

To do so, we have to _configure_ our model: give it a name, and possibly assets, dependencies, adding test cases, etc.

Models are made available to clients using `modelkit` by specifying them using the `CONFIGURATIONS` class attribute:

```python
class SimpleModel(Model):
    CONFIGURATIONS = {
        "simple": {}
    }
    def _predict(self, item):
        return "something"
```

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
    def _predict(self, item):
        return self.model_settings["value"]
```

Now, there are two versions of the model available, `simple` and `simple2`:

```python
from modelkit.core import ModelLibrary

p = ModelLibrary(models=SimpleModel)
m = p.get("simple")
print(m({}))
m2 = p.get("simple2")
print(m2({}))
```

It will print `"something"` and `"something2"`.

### Model attributes

In general, `Model` have several attributes set by the `ModelLibrary` when they are initialized:

- `asset_path` the path to the asset set in the `Model`'s configuration
- `configuration_key` the key of the model's configuration
- `model_dependencies` a dictionary of `Model` dependencies
- `model_settings` the `model_settings` as passed at initialization
- `service_settings` the settings of the `ModelLibrary` that created the model

And a set of attributes always present:

- `batch_size` the batch size for the model: if `_predict_batch` is implemented it will default to getting batches of this size. It defaults to `None`, which means "no batching"


### `Asset` class

It is sometimes useful for a given asset in memory to serve many different `Model` objects. It is possibly by using the `model_dependencies` to point to a parent `Model` that is the only one to load the asset via `_load`.

In this case, we may not want the parent asset-bearing `Model` object to implement `predict` at all.

This is what an `modelkit.core.model.Asset` is.

!!! note
    In fact, it is defined the other way around: `Model`s are `Asset`s with a predict function, and thus `Model` inherits from `Asset`.

!!! note
    There are two ways to use a data asset in a `Model`: either load it directly via its configuration and the `_load`, or package it in an `Asset` and use the deserialized object via model dependencies.


