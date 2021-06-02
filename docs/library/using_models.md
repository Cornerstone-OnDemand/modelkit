
## Consuming `modelkit` models

This section describes how to consume `modelkit` models.

The normal way to use `modelkit` models is by instantiating a `ModelLibrary` with a set of models.

```python
from modelkit import ModelLibrary, Model

class MyModel(Model):
    async def _predict(self, item):
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

!!! note "Shortcuts"

    For development, it is also possible to load a single model without a `ModelLibrary`:

    ```
    from modelkit import load_model
    model = load_model("my_favorite_model", models="package")
    ```

    If you have set the `MODELKIT_DEFAULT_PACKAGE` environment variable, you can also skip the `models=...` part.

Predictions can be obtained by calling the object:

```python
# This runs the Model method
prediction = model(item) # or model.predict(item)
# or
prediction = await model.predict_async(item)
```

Predictions for list of items can be obtained by using `predict_batch`:

```python
predictions = model.predict_batch(items)
# or
predictions = await model.predict_batch_async(items)
```

Which allows the user to leverage vectorized code by implementing `_predict_batch` instead of `_predict`.

# CLIs

Also see the CLIs documentation [here](../cli.md)
