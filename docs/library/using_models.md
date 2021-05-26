
## Consuming `modelkit` models

This section describes how to consume `modelkit` models.

### Installing `modelkit`

Make sure that the environment you plan to use `modelkit` on is setup as per [the guidelines](../configuration.md), and then either:

- install `modelkit` from `devpi` using `pip install modelkit`
- install `modelkit` from the repository using `python setup.py install`

!!! warning
    Do _not_ install `modelkit` in the same virtual environment you plan on
    developping `modelkit` with.

### Python package method

Clients use `modelkit` models by instantiating a `ModelLibrary` with a set of models
picked either amongst models defined in the `modelkit.library.model_configuration` module,
or by specifying a `modelkitModelConfiguration` at runtime.

In each case, the models are then accessed via `ModelLibrary.get("some name")`
 and used with `Model`.

Here is a typical implementation that uses an modelkit model configured as `my_favorite_model` somewhere under the `modelkit.models` module.

```python
from modelkit import ModelLibrary
import modelkit.models

# Create the prediction service
# This downloads all the assets and instantiates all the `Model`
# objects that were specified
service = ModelLibrary(models=modelkit.models)

# This is only a dictionary lookup
model = service.get("my_favorite_model")
```

!!! info "Shortcuts"

    For development, it is also possible to load a single model without a `ModelLibrary`:

    ```
    model = load_model("my_favorite_model")
    ```

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
