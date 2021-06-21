
The main concepts in `modelkit` are `Model` and the `ModelLibrary`.

The `ModelLibrary` instantiates and configures `Model` objects
and keeps track of them during execution. 

`Model` objects can then be requested via `ModelLibrary.get`, and used to make predictions via `Model.predict`. The ML logic is written in each `Model`'s `predict` functions, typically inside a module.

### Model and ModelLibrary

The normal way to use `modelkit` models is by **creating models** by subclassing the `modelkit.Model` class, and adding a configuration, then **creating a ModelLibrary** by instantiating a `ModelLibrary` with a set of models.

```python
from modelkit import ModelLibrary, Model

# Create a Model subclass
class MyModel(Model):
    # Give it a name
    CONFIGURATIONS = {"my_favorite_model": {}}

    # Write some prediction logic
    def _predict(self, item):
        return item


# Create the model library
library = ModelLibrary(models=MyModel)

# Get the model
model = library.get("my_favorite_model")

# Get predictions
model("hello world") # returns hello world
```


In the tutorial you will learn that:

- Models can have an **asset** linked to them, to store parameters, weights, or anything really. This asset is loaded and deserialized when the `ModelLibrary` instantiates the object.
- Models can **depend on other models** and share objects in memory (in particular, they can share assets). Only the minimal subset of models is loaded when a given model is required.
- Model inputs and outputs can be systematically validated using [pydantic](https://pydantic-docs.helpmanual.io/)
- Models can implement **vectorized** logic to make faster predictions.
- Models can implement **asynchronous** logic and be called either way.
- Models can serve Tensorflow models conveniently

