A model can implement a `_load` method that is called by `modelkit` either when loading the `model` through a `ModelLibrary` or when instantiating it.

This allows you to load information from an asset stored locally, or retrieved from an object store at run time. Assets may contain files, folders, parameters, optimized data structures, or anything really.

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


## Model with asset example

Adding the key to the model's configuration:

```python
class ModelWithAsset(Model):
    CONFIGURATIONS = {
        "model_with_asset": {"asset": "test/yolo:1"}
    }
```

Will cause the `ModelLibrary` to download `gs://bucket/assets/test/1/yolo` locally to the assets folder folder (which storage provider and bucket is used depends on your configuration), and set the `Model.asset_path` attribute accordingly.

It is up to the user to define the deserialization logic:

```python
class ModelWithAsset(Model):
    def _load(self):
        # For example, here, the asset is a BZ2 compressed JSON file
        with bz2.BZ2File(self.asset_path, "rb") as f:
            self.data_structure = pickle.load(f) # loads {"response": "YOLO les simpsons"}

    def _predict(self, item: Dict[str, str], **kwargs) -> float:
        return self.data_structure["response"] # returns "YOLO les simpsons"
```

!!! note
    Assets retrieval is handled by `modelkit`, and it is guaranteed that they be present when `_load` is called, even in lazy mode. However, it is not true when `__init__` is called. In general, it is not a good idea to subclass `__init__`.

## Asset convention and resolution

The string definition of an asset can be multiple things:

- an absolute path to a local file
- a relative path to a local file (relative to the current working directory)
- a relative path to a local file (relative to the directory set as an environment variable `MODELKIT_ASSETS_DIR`)
- an **asset specification** which can refer to assets stored remotely


### Remote assets

## Asset specification

The general asset specification is a string that follows the convention:

```
name/of/asset/object:version[/asset/subobject]
```
Where:
- version is a semantic version `major.minor` (e.g. `1.2`), and the missing information is resolved to the latest (e.g. `name/of/asset/object:1` is resolved to the latest minor version of `1.*`), or `name/of/asset/object` is resolved to the latest version
- `[/asset/subobject]` allows one to refer directly to a sub object, but is optional

Refer to [the assets documentation](../../assets/index.md) for more information about assets.

## Asset file override 

There are multiple ways to override the asset file for a model.

In simple situations, simply instantiating the `Model` with the `asset_path` will be enough:

```python
m = MyModel(asset_path="/a/path")
```

In situations in which the model is instantiated via a `ModelLibrary` in existing code, you can force to use a local file for a model by setting an environment variable: `MODELKIT_{}_FILE".format(model_asset.upper())`. 

Finally, it is also possible to set the override programmatically at the level of the `ModelLibrary`

```python
service = ModelLibrary(required_models =
        {
            "my_favorite_model":{
                "asset_path": "/path/to/asset"
            }
        }
    )
```