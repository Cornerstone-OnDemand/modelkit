
## Consuming `modelkit` models

This section describes how to consume `modelkit` models.

The normal way to use `modelkit` models is by instantiating a `ModelLibrary` with a set of models.

```python
from modelkit import ModelLibrary, Model

class MyModel(Model):
    def _predict(self, item):
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

### Predictions for single items

Predictions can be obtained by calling the object:

```python
prediction = model(item) # or model.predict(item)
```

This will call whichever one of `_predict` or `_predict_batch` was implemented in the `Model`.

### Predictions for lists of items

Predictions for list of items can be obtained by using `predict_batch`:

```python
predictions = model.predict_batch(items)
```

This will call whichever one of `_predict` or `_predict_batch` was implemented in the `Model`. 
But in the case in which `_predict_batch` is implemented, you may see speed ups due to vectorization.

### Predictions from iterators

It is also possible to iterate through predictions with an iterator, which is convenient to avoid having to load all items to memory before getting predictions.

```python
def generate_items():
    ...
    yield item
for prediction in model.predict_gen(generate_items()):
     # use prediction
    ...
```

A typical use case is to iterate through the lines of a file, perform some processing and write it straight back to another file



# CLIs

Also see the CLIs documentation [here](../cli.md)
