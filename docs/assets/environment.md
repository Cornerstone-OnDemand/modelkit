# Environment

## Model library

It is possible to set a default value of a package in which `ModelLibrary` will look for models:

| Environment variable | Default value | Notes |
| --- | --- | --- |
| `MODELKIT_DEFAULT_PACKAGE` | None | It has to be findable (on the `PYTHONPATH`) |
| `WORKING_DIR` | None | Local directory to find assets, has to exist |

## AssetsManager settings

The parameters necessary to instantiate an `AssetsManager` can all be read from environment variables, or provided when initializing the `AssetsManager`.

| Environment variable | Default value | Parameter | Notes |
| --- | --- | --- | --- |
| `STORAGE_PROVIDER` | `gcs` | `storage_provider` | `gcs` (default), `s3` or `local` |
| `ASSETS_BUCKET_NAME` | None | `bucket` | Bucket in which data is stored |
| `STORAGE_PREFIX` | `modelkit-assets` | `storage_prefix` | Objects prefix |
| `ASSETSMANAGER_TIMEOUT_S` | `300` | `timeout_s` | file lock timeout when downloading assets |

More settings can be passed in order to configure the driver itself.

### Storage driver settings

#### AWS storage

This storage provider is used locally and in production on AWS. We use [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) under the hood.

Then, configure the following variables:

| Environment variable    | Value |
| ----------------------- | ----- |
| `STORAGE_PROVIDER`      | `s3`  |
| `ASSETS_BUCKET_NAME`    |       |
| `AWS_ACCESS_KEY_ID`     |       |
| `AWS_SECRET_ACCESS_KEY` |       |
| `AWS_SESSION_TOKEN`     |       |
| `AWS_DEFAULT_REGION`    |       |
| `S3_ENDPOINT`           |       |

#### GCS storage

We use [google-cloud-storage](https://googleapis.dev/python/storage/latest/index.html).

| Environment variable             | Default value | Notes                 |
| -------------------------------- | ------------- | --------------------- |
| `GOOGLE_APPLICATION_CREDENTIALS` | None          | path to the JSON file |

By default, the GCS client use the credentials setup up on the machine.

If `GOOGLE_APPLICATION_CREDENTIALS` is provided, it should point to a local JSON service account file.

#### Local storage

The local storage method is mostly used for development, and should not be useful to end users.
It implements a `StorageDriver` from a local directory, that emulates other object providers.

In this case `ASSETS_BUCKET_NAME` describes a local folder from which assets will be pulled.

## Prediction Service

`OVERRIDE_STORAGE_PREFIX` is used to set ModelLibrary `override_storage_prefix` setting
