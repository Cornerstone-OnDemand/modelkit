# Assets directory structure

The `AssetsManager` persists assets locally for developmnet: when an asset is requested with 
`AssetsManager.fetch_asset` it checks whether an up-to-date version of the asset is present before downloading a new asset if necessary.

Assets are considered _immutable_ and versioned, no checks are performed to verify that the objects have not been manually changed locally.

## Fetching assets

The local asset directory is found at `ASSETS_DIR`, where both values
can be fed to the `AssetsManager` at initialization. 

Each asset's name is splitted along the path separators as directories, and 
version information is added.

For example, we have pushed to the remote store two assets: a directory to `some/directory/asset` and a file to `some/asset`. After retrieving them to the `assets_dir`, it will look like this:

```
assets_dir
└── some
|   ├── asset
|   │   ├── 0.0
|   │   ├── 0.1
|   │   |   ...
|   ├── directory
|   │   ├── asset
|   │   │   ├── 0.0
|   │   │   |   ├── content0
|   │   │   |   ├── content2
|   │   │   |   |   ...
|   │   │   ├── 0.1
|   │   │   |   |   ...
|    ...
```

To retrieve the assets path, it is enough to run:

```python
mng = AssetsManager(assets_dir=assets_dir)
mng.fetch_asset("some/asset:0.0") # will point to `some/asset/0.0`
mng.fetch_asset("some/directory/asset:0.1") # will point to `some/asset/0.1`
```
