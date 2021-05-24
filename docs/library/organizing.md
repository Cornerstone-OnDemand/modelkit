## Model organization

`modelkit` encourages you to organise models in python packages

```
PYTHONPATH
└── package
|   ├── __init__.py
|   ├── module.py
|   ├── module_2.py # defines sub_model
|   ├── subpackage
|   │   ├── __init__.py
|   │   ├── sub_module.py
|   │   |   ...
|   │   ...
```

To load all models in the package:
```python
from modelkit import ModelLibrary
import package

service = ModelLibrary(models=package)
```

or in a sub pacakge

```python
service = ModelLibrary(models=package.subpackage)
```

or in selected sub packages
```python
from modelkit import ModelLibrary
import package.subpackage

service = ModelLibrary(models=[package.module_2, package.subpackage])
```

To restrict the models that are being loaded, pass a list of models to the `ModelLibrary` instantiation:

```python
from modelkit import ModelLibrary
import package.subpackage

service = ModelLibrary(
    models=[package.module_2, package.subpackage],
    required_models=["some_model"]
    )
```
