## Overview

The main concepts in `modelkit` are `Model` and the `ModelLibrary`.

The `ModelLibrary` instantiates and configures `Model` objects
and keep track of them during execution.

`Model` objects can then be requested via `ModelLibrary.get`,
 and used to make predictions via `Model`.

The ML logic is written in each `Model`'s `predict` functions, typically inside a module.

### Quickstart

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
model = library.get("my_favorite_model")

model("hello world") # returns hello world
```

`Model` are much more powerful than this, in the tutorial you will learn that:

- Models can have an **asset** linked to them, to store parameters, weights, or anything. This asset is loaded and deserialized when the `ModelLibrary` isntantiates the object.
- Models can **depend on other models** and share objects in memory (in particular, they can share assets). Only the minimal subset of models is loaded when a given model is required.
- Model inputs and outputs can be systematically validated using [pydantic](https://pydantic-docs.helpmanual.io/)
- Models can implement **vectorized** logic to make faster predictions.
- Models can implement **asynchronous** logic and be called either way.
- Models can serve Tensorflow models conveniently

