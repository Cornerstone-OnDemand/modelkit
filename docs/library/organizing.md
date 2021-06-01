## Model organization

`modelkit` encourages you to organise models in python packages which can be tested and shared between members of the same team.

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

service = ModelLibrary(models=package)
```

!!! note 
    It is also possible to refer to a sub module `ModelLibrary(models=package.subpackage)` the `Model` classes themselves `ModelLibrary(models=SomeModelClass)`, string package names `ModelLibrary(models="package.module_2")` or any combination of the above `ModelLibrary(models=[package.subpackage, SomeModelClass])`

In order to restrict the models that are actually being loaded, pass a list of `required_models` keys to the `ModelLibrary` instantiation:

```python
service = ModelLibrary(
    models=[package.module_2, package.subpackage],
    required_models=["some_model"]
    )
```
