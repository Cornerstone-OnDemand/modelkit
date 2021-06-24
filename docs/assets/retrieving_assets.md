It is possible to access assets programmatically from their asset specification

Once you have correctly configured your environment and [storage provider](storage_provider.md):


```python
from modelkit.assets.manager import AssetsManager

mng = AssetsManager()
asset_path = mng.fetch_asset("asset_category/asset_name:version[sub/part]")

with open(asset_path, "r") as f:
    # do something with the asset
    ...

```

By default, `AssetsManager.fetch_asset` only returns the path to the locally downloaded asset, but it can return more information about the fetched asset if provided with the `return_info=True`.

In this case it returns a dictionary with:

```python
{
    "path": "/local/path/to/asset",
    "from_cache": True or False, # whether the asset was pulled from cache,
    "version": "returned asset version", # the asset version
    # These are present only when the asset was
    # downloaded from the remote store:
    "meta": {}, # contents of the meta JSON object 
    # remote object names
    "object_name": "remote object name", 
    "meta_object_name": "remote meta object name",
    "versions_object_name": "remote version object name"
}
```