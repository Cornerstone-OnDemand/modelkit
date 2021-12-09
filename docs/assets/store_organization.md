

## Remote asset storage convention

### Data object

Remote assets are stored in object stores, referenced as:

```
[provider]://[bucket]/[prefix]/[category]/[name]/[version]
```

In this "path":

- `provider` is `s3`, `azfs` or `gcs` or `file` depending on the storage driver (value of `MODELKIT_STORAGE_PROVIDER`)
- `bucket` is the remote container name (`MODELKIT_STORAGE_BUCKET`)

The rest of the "path" is the remote object's name and consists of

- `-prefix` is a prefix to all assets for a given `AssetsManager` (`MODELKIT_STORAGE_PREFIX`)
- `name` describes the asset. The name may contain path separators `/` but each file remotely will be stored as a single object.
- `version` describes the asset version in the form `X.Y`

!!! note
    If the asset is a directory, all sub files will be stored as 
    separate objects under this prefix.

### Meta object

In addition to the data, the asset object reside alongside a `*.meta` object:

```
[provider]://[bucket]/[prefix]/[category]/[name]/[version].meta
```

The `meta` is a JSON file containing

```python
{
    "push_date": "", # ISO date of push
    "is_directory": True or False, # whether the asset has mulitple objects
    "contents": [] # list of suffixes of contents when is_directory is True
}
```

### Version object

Assets have versions, following a `Major.Minor` version convention.

We maintain a `versions` JSON file in order to keep track of the latest version. 
This avoids having to list objects by prefix on objects store, which is typically a very time consuming query.

It is stored at
```
[provider]://[bucket]/[assetsmanager-prefix]/[category]/[name].versions
```

And contains
```
{
    "versions": [], # list of ordered versions, latest first
}
```

!!! note 
    This is the only object on the object store that is *not immutable*. It is updated whenever an asset is updated.