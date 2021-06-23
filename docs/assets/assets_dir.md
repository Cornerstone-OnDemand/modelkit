When used with a remote storage provider, `modelkit` will persist assets locally in the assets directory. This is very useful for development, whenever an asset is requested `modelkit` will first check if it is present before downloading the remote asset if necessary.

Because [assets are considered _immutable_](remote_assets.md), no checks are performed to verify that the objects have not been manually changed locally.

## Assets directory

The local asset directory is found at `ASSETS_DIR`, although this can also be overrident when instantiating an `AssetsManager`.

Each asset's name is splitted along the path separators as directories, and 
version information is added.

For example, we have pushed to the remote store two assets: a directory to `some/directory/asset` and a file to `some/asset`. After retrieving them to the `assets_dir`, it will look like this:

```
ASSETS_DIR
└── some
|   ├── asset
|   │   ├── 0.0 # <- the file content
|   │   ├── .0.0.SUCCESS # hidden file indicating download success
|   │   ├── 0.1
|   │   |   ...
|   ├── directory
|   │   ├── asset
|   │   │   ├── 0.0
|   │   │   |   ├── .SUCCESS # hidden file indicating download success
|   │   │   |   ├── content0  <- the directory contents
|   │   │   |   ├── content2
|   │   │   |   |   ...
|   │   │   ├── 0.1
|   │   │   |   |   ...
|    ...
```

!!! note
    All previous versions of the assets are kept locally. It is save, however to delete local copies of the assets manually to save space.

    For directory assets, delete the version directory. For file assets, do not forget to delete the `.version.SUCCESS` file too.

To retrieve the assets path, refer to it via its asset specification:

```python
mng = AssetsManager(assets_dir=assets_dir)
mng.fetch_asset("some/asset:0.0") # will point to `ASSETS_DIR/some/asset/0.0`
mng.fetch_asset("some/directory/asset:0.1") # will point to `ASSETS_DIR/some/asset/0.1`
mng.fetch_asset("some/directory/asset:0.1[content0]") # will point to `ASSETS_DIR/some/asset/0.1/content0`
```

## Version resolution

When an asset is request with the `version` not fully specified, `modelkit` may need to consult the remote storage to find the latest version. As a result, `modelkit`'s asset manager will in this context have a different behavior depending on whether a remote storage provider is parametrized:

- **Without a remote store** find the latest version of the asset available in the `ASSETS_DIR`
- **With a remote store** contact the remote store to find the latest version, see if it is present locally. If it is, use the local version, otherwise download the latest version.

This has an important consequence, which is that unpinned assets will always require network calls when being fetched, although they may already be present. For all production purposes, you should **pin your asset versions**.