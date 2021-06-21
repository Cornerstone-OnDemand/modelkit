In `modelkit`, a `Model` is simply a subclass of `modelkit.Model` that implements a `_predict` function.

```python
from modelkit import Model

class MyModel(Model):
    def _predict(self, item):
        ...
        # prediction code goes here
        ...
        return result
```
And that's it!

With this little boilerplate code, you can now call the model to get predictions, have them batched, or exposed in an API, etc.

## Instantiating Models

### Simple models

Very simple `Model` objects can be created and instantiated straight away, that is when they do not load complex assets, or rely on other `Model` objects for their execution. For example:

```python
from modelkit import Model

class MyModel(Model):
    def _predict(self, item):
        return item

m = MyModel()
```

### Complex models

In general, however, to resolve assets, dependencies, etc. `modelkit` models need to be instantiated using `ModelLibrary` with a set of models.

Models are then accessed via `ModelLibrary.get("some name")`.
 
For example, to load a model that has one dependency:

```python
from modelkit import ModelLibrary, Model

# Create two models, with names
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
        return self.model_dependencies["a_model"].predict(item)

# Create the model library
# This loads the required models (including their dependencies)
library = ModelLibrary(
    required_models=["my_favorite_model"],
    models=[MyModel, MyComposedModel]
)

# This is only a dictionary lookup
model = library.get("my_favorite_model")
```

The library gives you access to all the models from a single object, and deals with instantiation of the necessary objects. 
Furthermore, `modelkit` encourages you to store your models in a Python package (see [Organization](organizing.md)).
