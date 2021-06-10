
## Consuming `modelkit` models


### Loading models

#### Simple case

Simple `Model` objects can be created and instantiated straight away

```python
from modelkit import Model

class MyModel(Model):
    def _predict(self, item):
        return item

m = MyModel()
```

In this case, however, the `Model` does not have any `model_dependencies` or `asset`.

#### General case

In general, to resolve assets and dependencies, `modelkit` models need to be instantiated using `ModelLibrary` with a set of models.
Models are then accessed via `ModelLibrary.get("some name")`.
 
For example, to load a model that has one dependency:

```python
from modelkit import ModelLibrary, Model

class MyModel(Model):
    CONFIGURATIONS = {
        "a_model" : {}
    }
    def _predict(self, item):
        return item

class MyComposedModel(Model):
    CONFIGURATIONS = {
        "my_favorite_model" : {
            "model_dependencies": {"a_model"}
        }
    }
    def _predict(self, item):
        return item

# Create the model library
# This downloads all the assets and instantiates all the `Model`
# objects that were specified
library = ModelLibrary(models=[MyModel, MyComposedModel])

# This is only a dictionary lookup
model = library.get("my_favorite_model")
```

#### From a package

`modelkit` encourages you to store your models in a Python package (see [Organization](organizing.md)).

For example, assuming we have a modelkit model configured as `my_favorite_model` somewhere under the `my_models` module.

```python
from modelkit import ModelLibrary
import my_models # contains subclasses of `Model`

# Create the library
# This downloads assets and instantiates model_dependencies
library = ModelLibrary(models=my_models)
model = library.get("my_favorite_model")
```

!!! note "Shortcuts"

    For development, it is also possible to load a single model without a `ModelLibrary`:

    ```python
    from modelkit import load_model
    model = load_model("my_favorite_model", models="my_models")
    ```

    If you have set the `MODELKIT_DEFAULT_PACKAGE` environment variable, you can also skip the `models=...` part.

### Getting model predictions

#### Predictions for single items

Predictions can be obtained by calling the object:

```python
prediction = model(item) # or model.predict(item)
```

This will call whichever one of `_predict` or `_predict_batch` was implemented in the `Model`.

#### Predictions for lists of items

Predictions for list of items can be obtained by using `predict_batch`:

```python
predictions = model.predict_batch(items)
```

This will call whichever one of `_predict` or `_predict_batch` was implemented in the `Model`. 
But in the case in which `_predict_batch` is implemented, you may see speed ups due to vectorization.

??? optional-class "Example"
    In this example, we implement a dummy `Model` that computes the position
    of the min in a list using `np.argmin`. 

    In one version the code is not vectorized (it operates on a single item)
    and in the other one it is (a whole batched is processed at once).

    The vectorized version is ~50% faster
    ```python
    import random
    import timeit

    from modelkit.core.model import Model
    import numpy as np

    # Create some data
    data = []
    base_item = list(range(100))
    for _ in range(128):
        random.shuffle(base_item)
        data.append(list(base_item))

    # This model is not vectorized, `np.argmin`
    # will be called individually for each batch
    class MinModel(Model):
        def _predict(self, item):
            return np.argmin(item)


    m = MinModel()

    # This model is vectorized, `np.argmin`
    # is called over a whole batch
    class MinBatchedModel(Model):
        def _predict_batch(self, items):
            return np.argmin(items, axis=1)


    m_batched = MinBatchedModel()

    # They do return the same results
    assert m.predict_batch(data) == m_batched.predict_batch(data)


    # The batched model is ~50% slower
    timeit.timeit(lambda: m.predict_batch(data), number=1000)
    # The batched model is ~50% slower
    timeit.timeit(lambda: m_batched.predict_batch(data), number=1000)
    # Even more so with a larger batch size
    timeit.timeit(lambda: m_batched.predict_batch(data, batch_size=128), number=1000)
    ```

#### Predictions from iterators

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


