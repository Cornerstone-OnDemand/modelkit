
## Consuming `modelkit` models

This section describes how to consume `modelkit` models.

The normal way to use `modelkit` models is by instantiating a `ModelLibrary` with a set of models.

```python
from modelkit import ModelLibrary, Model

class MyModel(Model):
    async def _predict_one(self, item):
        return item


# Create the model library
# This downloads all the assets and instantiates all the `Model`
# objects that were specified
library = ModelLibrary(models=MyModel)

# This is only a dictionary lookup
model = library.get_model("my_favorite_model")
```

In each case, the models are then accessed via `ModelLibrary.get("some name")`
 and used with `Model`.

Here is a typical implementation that uses an modelkit model configured as `my_favorite_model` somewhere under the `modelkit.models` module.

```python
from modelkit import ModelLibrary

# Create the prediction service
# This downloads all the assets and instantiates all the `Model`
# objects that were specified
library = ModelLibrary(models=modelkit.models)

# This is only a dictionary lookup
model = library.get("my_favorite_model")
```

!!! info "Shortcuts"

    For development, it is also possible to load a single model without a `ModelLibrary`:

    ```
    from modelkit import load_model
    model = load_model("my_favorite_model", models="package")
    ```

    If you have set the `MODELKIT_DEFAULT_PACKAGE` environment variable, you can also skip the `models=...` part.

Predictions can be obtained either for a single item (usually a dict), or a _list of items_
via the same predict method:

```python
# This runs the Model method
prediction = model(item)
# or
prediction = await model_async(item)
```

If `predict` (or `predict_async`) sees a list, it will call `_predict_multiple` and
return a list of processed items (possibly leveraging batching/vectorization
for performance).

If `predict` sees something else it will try to call `_predict_one` on it and return the
response for a single item.
# CLIs

Also see the CLIs documentation [here](../cli.md)
