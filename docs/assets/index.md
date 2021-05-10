`modelkit.assets` contains code to create, upload, update and retrieve data assets on the
object store.

## API

In order to retrieve an asset:

```python
from modelkit.assets.manager import AssetsManager

mng = AssetsManager()
asset_path = mng.fetch_asset("asset_category/asset_name:version")

with open(asset_path, "r") as f:
    # do something

```

!!! warning
    You need to [configure your environment](environment.md) to run this code.

## CLI

To list all assets:
```bash
$ assets list
```

To create a new asset:
```bash
$ assets new /path/to/asset asset_category/asset_name
```

To update an asset's minor version:

```bash
$ assets update /path/to/asset asset_category/asset_name
```

To push a new major version:
```bash
$ assets update /path/to/asset asset_category/asset_name --bump-major
```
