# Working directory structure

The `AssetsManager` implements a caching system: when an asset is requested with 
`AssetsManager.fetch_asset` it checks in its caching directory, whether an up-to-date version of the asset is present.

To do so, the hash of the file is read from the remote storage and compared to the 
hash found locally. If they match, the asset is not downloaded and directly provided 
from the local caching directory. Otherwise, the local asset is overwritten with 
the version read from the remote directory.


## Fetching assets

The caching directory is found at `working_dir/storage_prefix`, where both values
can be fed to the `AssetsManager` at initialization. 

The directory structure is as follows:

```
working_dir
└── storage_prefix
|   ├── .cache
|   │   ├── category0
|   │   │   ├── name0
|   │   │   |    ├── 0.0.meta
|   │   │   |    ├── [0.0.tmp]
|   │   │   |    |   ...
|   │   │   ├── name1
|   │   │   |    |   ...
|   │   ├── category1
|   │   │   |    ...
|   ├── category
|   │   ├── name0-0.0[.ext]
|   │   ├── name1-0.0
|   │   |   ...
├── [other storage_prefix]
|    ...
```

The working dir is separated between different folders named after each `AssetsManager`'s
`storage_prefix`. Each contains a `.cache` directory with:
  *  the `*.meta` JSON files that are used to compare the local version with
the remote version and decide whether to re-download assets
  *  the `*.tmp` files: downloaded asset archives, present only before being moved
    to their final position.

It also contains a subdirectory for each asset category, each containing the local assets, either the asset itself named `name-version.extention`  (if it is a file), or the asset directory `name-version` with the asset contents.