This section describes how to push assets either manually using CLI or programmatically.

## General considerations

There are two separate actions one can take to affect the remotely stored assets:

- _update_ an existing asset: If the asset already exists remotely (and, in particular
  has a `.versions` object present), the appropriate action is to _update_ it. It is
  possible to update the `minor` version (the default behavior), or the `major` version.
- _create_ a new asset: If this is the first time that this asset is created, the correct
  action is the create it, which will assign it the `0.0` version.

## Maintaining assets programmatically

First, instantiate an `AssetsManager` pointing to the desired `bucket`, possibly changing
the `assetsmanager_prefix`, storage method, etc.:

```python
from modelkit.assets.manager import AssetsManager

assets_manager = AssetsManager(bucket=..., ...)
```

### Updating the asset

Assuming the asset is locally present at `asset_path` (either a file or a directory),
update the remote asset `name` as follows:

```python
assets_manager.update_asset(
  asset_path,
  name,
  bump_major=False,
  major=None
)
```

This will bump the latest existing version's minor version: `V.v => V.(v+1)`

Options:

- `bump_major`: If `True`, will bump the major version of the asset and create a `(V+1).0` asset (assuming `V` is the highest existing major version)
- `major=V`: If not falsy, will bump the minor version of the latest asset version with major version `V`:  `V.v => V.(v+1)`

### Creating a new asset

Assuming the asset is locally present at `asset_path` (either a file or a directory),
create the remote asset `name:0.0` as follows:

```python
assets_manager.create_asset(asset_path, name)
```

!!! warning
    Creating new assets programmatically is likely not a very good idea.
    Just do it manually once using the CLI.


## Maintaining assets with CLI

`bin/assets.py` implements CLIs to ease the maintenance of remote assets.


Use `--bucket` or `--assetsmanager-prefix` to affect the remote bucket and prefix for the
CLI you are using.

Alternatively one can also use environment variables as per [Environment](environment.md) to
affect the remote storage and `AssetsManager` parameters.


### Creating a new asset

To create a new asset:

```
bin/asset.py new /path/to/asset asset_name
```

After prompting your for confirmation, it will create a remote asset with version `0.0`.

### Updating the asset

Use `bin.asset.py update` to update an existing asset using a local file or directory
at `/local/asset/path`.


#### Bumping the minor version

Assuming `name` has versions `0.1`, `1.1`, running
```
bin/asset.py update /local/asset/path name
```
will add a version `1.2`


#### Bumping the major version

Assuming `name` has versions `0.1`, `1.0`, running

```
bin/asset.py update /local/asset/path name --bump-major
```

After prompting your for confirmation, it will add a version `2.0`


#### Bumping the minor version of an older asset

Assuming `name` has versions `0.1`, `1.0`, running

```
bin/asset.py update /local/asset/path name:0
```
will add a version `0.2`


### Listing remote assets

A CLI is available to list remote assets in a given bucket:

```
bin/asset.py list
```
