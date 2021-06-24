This section describes how to push assets either manually using CLI or programmatically.

## Asset maintenance actions

Since assets are immutable, there are only two actions one can take to affect the remotely stored assets.

- _update_ an existing asset: If the *asset name* already exists remotely, the appropriate action is to _update_ it. It is possible to update either the `minor` version, or the `major` version.
- _create_ a new asset: If this is the first time that this asset *asset name*  is created, the correct action is the create it, which will assign it the `0.0` version.

`modelkit` does not offer ways to delete or replace assets.

## Maintaining assets with CLI

`modelkit` implements CLIs to ease the maintenance of remote assets.

Make sure the storage provider is properly setup with environment variables (see [here](assets/../storage_provider.md)).


### Create a new asset

To create a new asset:

```
modelkit assets new /path/to/asset/locally asset_name
```

After prompting you for confirmation, it will create a remote asset with version `0.0`.

### Update an asset

Use `modelkit assets update` to update an existing asset using a local file or directory at `/local/asset/path`.

#### Bump the minor version

Assuming `name` has versions `0.1`, `1.1`, running
```
modelkit assets update /local/asset/path name
```
will add a version `1.2`


#### Bump the major version

Assuming `name` has versions `0.1`, `1.0`, running

```
modelkit assets update /local/asset/path name --bump-major
```

After prompting your for confirmation, it will add a version `2.0`


#### Bump the minor version of an older asset

Assuming `name` has versions `0.1`, `1.0`, running

```
modelkit assets update /local/asset/path name:0
```
will add a version `0.2`


### Listing remote assets

A CLI is also available to list remote assets in a given bucket:

```
modelkit assets list
```

## Maintaining assets programmatically

First, instantiate an `AssetsManager` pointing to the desired `bucket`, possibly changing the `storage_prefix`, storage method, etc.:

```python
from modelkit.assets.remote import RemoteAssetsStore

assets_store = RemoteAssetsStore()
```

### Create a new asset

Assuming the asset is locally present at `asset_path` (either a file or a directory),
create the remote asset `name:0.0` as follows:

```python
assets_store.new(asset_path, name)
```

!!! important
    Creating new assets programmatically is possible, even though it is not considered a good practice.
    Using the CLI is the prefered and safest way to manage assets.



### Update the asset

Assuming the asset is locally present at `asset_path` (either a file or a directory), update the remote asset `name` as follows:

```python
assets_store.update(
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
