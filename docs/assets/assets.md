# Assets

An asset is a file or a directory that is typically shared and stored on a remote object store (such as GCS or S3).

`modelkit` has tooling to push and retrieve these assets.

- At runtime, the `ModelLibrary` will retrieve the necessary assets from the object store, and store them locally. The paths to these assets is then passed to each `Model` instance which can then load the relevant parts.
- For developers, since the assets are versioned, they can be persisted locally in an `ASSETS_DIR`, thus they are only ever downloaded once.

## AssetsManager

An `AssetsManager` instance can be explicitly created as follows:

```python
from modelkit.assets.manager import AssetsManager

asset_manager = AssetsManager(assets_dir="/path/to/local/dir")
```

In this case, assets will be looked up locally under the `assets_dir`.

`modelkit` expects a particular directory structure in which to find the assets. 

In addition, the `AssetsManager` can be provided with an `storage_prefix` which
prefixes all stored assets (`modelkit-assets` by default).

### Fetching assets

The `AssetsManager.fetch_asset` method takes a string specification of the asset in the
form `asset_category/asset_name:version`.

The specification:

  - may contain exact specification of the version: `asset_category/asset_name:1.10`
  points to the exact `1.10` version
  - may omit the minor version: `asset_category/asset_name:1` points to the latest
  available version `1.*`
  - may omit version: `asset_category/asset_name` points to the latest version `*.*`

!!! note
    Keep in mind that the asset name can contain any number of separators (`/`).


By default, `AssetsManager.fetch_asset` only returns the path to the locally downloaded
asset, but it can return more information about the fetched asset if provided with the `return_info=True`.

In this case it returns a dictionary with:

```
{
  "path": "/local/path/to/asset",
  "from_cache": whether the asset was pulled from cache,
  "meta": {contents of the meta JSON object},
  "version": "returned asset version",
  "object_name": remote object name,
  "meta_object_name": remote meta object name,
  "versions_object_name": remote version object name
}
```

## Remote asset storage convention

### Data object

Remote assets are stored in object stores, referenced as:

```
[provider]://[bucket]/[assetsmanager-prefix]/[category]/[name]/[version]
```

!!! note
  If the asset consists in a directory, all sub files will be stored as 
  separate objects with this prefix.

In this "path":

- provider is `s3` or `gcs` or `file` depending on the storage driver
- `bucket` is the remote container name

The rest of the "path" is the remote object's name and consists of

- `assetsmanager-prefix` is a prefix to all assets for a given `AssetsManager`
- `name` describes the asset. The name may contain path separators `/` but each file remotely will be stored as a single object.
- `version` describes the asset version in the form `X.Y`

### Meta object

In addition to the data, the asset object reside alongside a `*.meta` object:

```
[provider]://[bucket]/[assetsmanager-prefix]/[category]/[name]/[version].meta
```

The `meta` is a JSON file containing

```
{
    "push_date": [ISO date of push],
    "is_directory": [bool]
    "hash": [content hash]
}
```

#### Asset compression

The behavior of the `AssetsManager` depends on whether the local asset being pushed is
a directory or a file:

- If it is a file, then it is pushed as-is, without being compressed
- If it is a directory, it is pushed as a `tar.gz` file. It is uncompressed upon being
  fetched, such that the path returned by `AssetsManager.fetch_asset` is a directory.

This information is stored in the metadata file.

### Version object

Assets have versions, following a `Major.Minor` version convention.

We maintain a `versions` JSON file in order to keep track of the latest version.

It is stored at
```
[provider]://[bucket]/[assetsmanager-prefix]/[category]/[name].versions
```

And contains
```
{
    "versions": [list of ordered versions, latest first]
}
```
