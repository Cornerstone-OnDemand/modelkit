# Configuration

## Environment

In order to run/deploy `modelkit` endpoints, you need to provide it with the necessary environment variables, most of them required by `modelkit.assets` to retrieve assets from the remote object store:

### General `modelkit` environment variables

The assets directory is required to know where to find assets

- `MODELKIT_ASSETS_DIR`: the local directory in which assets will be
  downloaded and cached. This needs to be a valid local directory.

It is convenient to set a default value of a package in which `ModelLibrary` will look for models:

- `MODELKIT_DEFAULT_PACKAGE` (default `None`). It has to be findable (on the `PYTHONPATH`)

Lazy loading is useful when you want the models to be loaded only when they are actually used.

- `MODELKIT_LAZY_LOADING` (defaults to `False`) toggles lazy loading mode for the `ModelLibrary`

Due to the implementation of cloud drivers, which are not pickable, the lazy driver mode is useful when you want 
to use the ModelLibrary in conjunction with libraries using pickle: PySpark, multiprocessing etc.

- `MODELKIT_LAZY_DRIVER` (defaults to `False`) toggles lazy mode for the `StorageProvider`'s drivers creation (boto3, gcs, azure)

### Storage related environment variables

These variables are necessary to set a remote storage from which to retrieve assets. Refer to the [storage provider documentation for more information](assets/storage_provider.md) for more information.

- `MODELKIT_STORAGE_BUCKET` (default: unset): override storage container
  where assets are retrieved from.
- `MODELKIT_STORAGE_PREFIX` : the prefix under which objects are stored
- `MODELKIT_STORAGE_PROVIDER` (default: `gcs`) the storage provider (does not have to be set)
    - for `MODELKIT_STORAGE_PROVIDER=gcs`, the variable `GOOGLE_APPLICATION_CREDENTIALS` need to be
      pointing to a service account credentials JSON file (this is not necessary on dev
      machines)
    - for `MODELKIT_STORAGE_PROVIDER=s3`, you need to instantiate `AWS_PROFILE`
    - for `MODELKIT_STORAGE_PROVIDER=az`, you need to instantiate `AZURE_STORAGE_CONNECTION_STRING` with a connection string

### Assets versioning related environment variable

 - `MODELKIT_ASSETS_VERSIONING_SYSTEM` will fix the assets versioning system. It can be `major_minor` or `simple_date`

### TF serving environment variables

These environment variables can be used to parametrize tensorflow serving.

- `MODELKIT_TF_SERVING_ENABLE` (default: `True`): Get tensorflow data from tensorflow server, instead of loading these data locally (if set to `False` you need to install tensorflow).
    - `MODELKIT_TF_SERVING_HOST` (default: `localhost`): IP address of tensorflow server
    - `MODELKIT_TF_SERVING_PORT` (default: `8501`): Port of tensorflow server
    - `MODELKIT_TF_SERVING_MODE` (default: `rest`): `rest` to use REST protocol of tensorflow server (port 8501), `grpc` to use GRPC protocol (port 8500)
    - `TF_SERVING_TIMEOUT_S` (default: `60`): Timeout duration for tensorflow server calls

### Cache environment variables

These environment variables can be used to parametrize the caching.

- `MODELKIT_CACHE_PROVIDER` (default: `None`) to use prediction caching
  - if `MODELKIT_CACHE_PROVIDER=redis`, use an external redis instance for caching:
    - `MODELKIT_CACHE_HOST` (default: `localhost`)
    - `MODELKIT_CACHE_PORT` (default: `6379`)
  - if `MODELKIT_CACHE_PROVIDER=native` use native caching (via [cachetools](https://cachetools.readthedocs.io/en/stable/)):
    - `MODELKIT_CACHE_IMPLEMENTATION` can be 
    - `MODELKIT_CACHE_MAX_SIZE` size of the cache
