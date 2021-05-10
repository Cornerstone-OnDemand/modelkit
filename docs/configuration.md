# Configuration

## Environment

In order to run/deploy `modelkit` endpoints, you need to provide it with the necessary environment variables, most of them required by `modelkit.assets` to retrieve assets from the remote object store:

- `ASSETS_BUCKET_NAME` (default: unset): override storage container
  where assets are retrieved from.
- `WORKING_DIR`: the local directory in which assets will be
  downloaded and cached. This needs to be a valid local directory.
- `STORAGE_PROVIDER` (default: `gcs`) the storage provider (does not have to be set)
    - for `STORAGE_PROVIDER=gcs`, the variable `GOOGLE_APPLICATION_CREDENTIALS` need to be
      pointing to a service account credentials JSON file (this is not necessary on dev
      machines)
    - for `STORAGE_PROVIDER=s3ssm`, you need to instantiate `AWS_PROFILE`

Refer to the [AssetsManager settings documentation](assets/environment.md) for more information.

- `LAZY_LOADING` (defaults to `False`) toggles lazy loading mode for the `ModelLibrary`
- `ENABLE_TF_SERVING` (default: `True`): Get tensorflow data from tensorflow server, instead of loading these data locally (if set to `False` you need to install tensorflow).
    - `TF_SERVING_HOST` (default: `localhost`): IP address of tensorflow server
    - `TF_SERVING_PORT` (default: `8501`): Port of tensorflow server
    - `TF_SERVING_MODE` (default: `rest`): `rest` to use REST protocol of tensorflow server (port 8501), `grpc` to use GRPC protocol (port 8500)
    - `TF_SERVING_TIMEOUT_S` (default: `60`): Timeout duration for tensorflow server calls
- `ENABLE_REDIS_CACHE` (default: `False) to use prediction caching
    - `CACHE_HOST` (default: `localhost`)
    - `CACHE_PORT` (default: `6379`)
- `modelkit_ASYNC_MODE` (default to `None`) forces the `DistantHTTPModels` to use async mode.

## New Assets Testing Environment

Developer can test new assets without having to add them to `ASSET_PREFIX`.

`OVERRIDE_ASSET_PREFIX` override `ASSET_PREFIX`.

`modelkit` will firstly try to download the assets from `OVERRIDE_ASSET_PREFIX`
(in which the developper pushed his new assets to test) before falling back to `ASSET_PREFIX`

## Dependencies

`modelkit` requires Python 3.7. You can use `pyenv` or `anaconda` to install it.

We recommend using a virtual environment. Then, in order to install modelkit dependencies, use:

```
pip install -r requirements.txt
```

Or to also install the developer tools (testing, etc.):

```
pip install -r requirements-dev.txt
```

If necessary, you have to install manually the tensorflow dependency:

```
pip install modelkit[tensorflow]
```
