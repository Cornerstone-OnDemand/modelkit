A model can implement a `_load` method that is called by `modelkit` either when loading the `model` through a `ModelLibrary` or when instantiating it. 

This allows you to load information from a files or folders stored locally (or retrieved from an object store). These can contain arbitrary files, folders, parameters, optimized data structures, or anything really.

`modelkit` ensures that it is only ever called once, regardless of how many times you want to use your model.

`modelkit` refers to these supporting files and directories used to load model as **assets**.

## Defining a model asset

The model asset is specified in the `CONFIGURATIONS` under the `asset` key: 

```python
class ModelWithAsset(Model):
    CONFIGURATIONS = {
        "model_with_asset": {"asset": "some_file.txt"}
    }

    def _load(self):
        with open(self.asset_path) as f:
            ...
```

When the `_load` method is called, the object will have an `asset_path` attribute that points to the absolute path of the asset locally.
`modelkit` will ensure that the file is actually present before `_load` is called.

The `_load` method is used to load the relevant information from the asset file(s).

### Asset convention and resolution

The string definition of an asset in the `CONFIGURATIONS` can refer to different things:

- an absolute path to a local file
- a relative path to a local file (relative to the current working directory)
- a relative path to a local file (relative to the "assets directory" a directory typically set with an environment variable `MODELKIT_ASSETS_DIR`)
- an **asset specification** which can refer to assets stored remotely

We encourage you to use **Asset specification** with **remote asset storage**, in order to get all the power of `modelkit` asset system.

## Other dependencies usable during `_load`

Whenever `_load` is called, `modelkit` ensures that all other dependencies are already loaded and ready to go. These include:

- `asset_path` the path to the asset (which is guaranteed to be present when it is called)
- `model_settings` as present in the `CONFIGURATIONS`
- `model_dependencies` are fully loaded
- `service_settings` the settings of the `ModelLibrary` 

### `_load` vs. `__init__`

Assets retrieval, dependencies management, are all handled for you by `modelkit.ModelLibrary`. For some features, it is necessary to instantiate the objects first, and only after resolve all assets and dependencies (e.g. in lazy mode, which is useful for Spark for example).

As a result it is only guaranteed that attributes will be present when `_load` is called, rather than `__init__`. This is why it is not in general a good idea to override `__init__` (or instantiate the models without the help of a `ModelLibrary`. 

