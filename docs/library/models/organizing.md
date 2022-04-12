## Models organization

`modelkit` encourages you to organise models in python packages which can be tested and shared between members of the same team.

### ModelLibrary from a package

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

### Organizing code

A typical `modelkit` model repository follows the same organisation as any other Python package.

```
PYTHONPATH
└── my_ml_package
|   ├── __init__.py
|   ├── module.py
|   ├── module_2.py # defines sub_model
|   ├── subpackage
|   │   ├── __init__.py
|   │   ├── sub_module.py
|   │   |   ...
|   │   ...
```

`modelkit` can make all packages available in a single `ModelLibrary` as so:

```python
from modelkit import ModelLibrary
import my_ml_package

service = ModelLibrary(models=my_ml_package)
```

> **Note:**<br>
It is also possible to refer to a sub module `ModelLibrary(models=package.subpackage)` the `Model` classes themselves `ModelLibrary(models=SomeModelClass)`, string package names `ModelLibrary(models="package.module_2")` or any combination of the above `ModelLibrary(models=[package.subpackage, SomeModelClass])`

In order to restrict the models that are actually being loaded, pass a list of `required_models` keys to the `ModelLibrary` instantiation:

```python
service = ModelLibrary(
    models=[package.module_2, package.subpackage],
    required_models=["some_model"]
)
```

### Abstract models

It is possible to define models that inherit from an abstract model in order to share common behavior. It only requires to not set CONFIGURATIONS dict for those models to be ignored from the configuration steps.

For instance, it can be usefull to implement common prediction algorithm on different data assets.

```python
class BaseModel(Model):
    def _predict(self, item, **kwargs):
        ...

class DerivedModel(BaseModel):
    CONFIGURATIONS = {"derived": {"asset": "something.txt"}}

    def _load(self):
        ...
```
