Remote assets allow you to share the necessary files and folders necessary to run your models with other members of your team, as well as with production services.

In addition `modelkit` helps with the versioning of these files, and the management of your local developer copies.

## Remote asset properties

For `modelkit` remote assets are **immutable**, and their source of truth has to be a single remote object store. These have the following advantages:

- **auditing** it is possible to know which asset was used when by a production service, and pushed by whom
- **reverting** it is always possible to revert to an older version of a `Model` because assets will be present and cannot be modified.
- **loss of data** local machines can lose all of their data, assets will always be available from the remote store
- **reproducibility** the code running on your local machine is guaranteed to use the same artifacts and code as the one running in production

Although these come at a cost, `modelkit` helps you manage, update, and create new assets.

It also helps with maintaining your local copies of the assets to make development quicker (in the **assets directory**).

## Model with remote asset

Using a remote asset in a `Model` is exactly the same thing as using a local one and using `_load` as [we have seen before](../library/models/model_with_load.md).

We add a valid **remote asset specification** as a key in the configuration,
`modelkit` will make sure to retrieve it before the `Model` is instantiated:

```python
class ModelWithAsset(Model):
    CONFIGURATIONS = {
        "model_with_asset": {"asset": "test/asset:1"} # meaning "version 1 of test/asset"
    }
```

Assuming that you have parametrized a GCS object store, this will cause the `ModelLibrary` to:

- download the objects at `gs://some-bucket-name/assets/test/1/yolo/*` locally (which storage provider and bucket is used depends on [your configuration](storage_provider.md))
- write the files to the *assets directory* (controlled by `ASSETS_DIR`)
- set the `Model.asset_path` attribute accordingly.

As a result, you can still write your own arbitrary `_load` logic, with confidence that the asset will actually be here

```python
class ModelWithAsset(Model):
    def _load(self):
        # For example, here, the asset is a BZ2 compressed JSON file
        with bz2.BZ2File(self.asset_path, "rb") as f:
            self.data_structure = pickle.load(f) # loads {"response": "Hello World!"}

    def _predict(self, item, **kwargs):
        return self.data_structure["response"] # returns "Hello World!"
```

## Asset specification

An **asset specification string** follows the convention:

```
name/of/asset/object:version[/asset/subobject]
```

Where:

- the name of the asset has to be a valid object store name (using `/` as a prefix separator)
- `version` follows a semantic versioning system: (by default `major.minor` (e.g. `1.2`))
- `[/asset/subobject]` optionally allows one to refer directly to a `sub object

### Version resolution

Whenever a version is not completely set, the missing information is resolved to the latest version. For example:

- `name/of/asset/object` is resolved to the latest version altogether

Some versioning system can support partial version setting

Example for major/minor system :

- `name/of/asset/object:1` is resolved to the latest minor version `1.*`

