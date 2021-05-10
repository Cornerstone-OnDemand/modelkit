# Environment

## AssetsManager settings

The parameters necessary to instantiate an `AssetsManager` can all be read from environment variables, or provided when initializing the `AssetsManager`.

| Environment variable      | Default value | Parameter              | Notes                                     |
| ------------------------- | ------------- | ---------------------- | ----------------------------------------- |
| `STORAGE_PROVIDER`        | `gcs`         | `storage_provider`     | `gcs` (default), `s3`, `s3ssm` or `local` |
| `ASSETS_BUCKET_NAME`      | None          | `bucket`               | Bucket in which data is stored            |
| `WORKING_DIR`             | None          | `working_dir`          | Local directory to cache assets           |
| `ASSETS_PREFIX`           | `assets-v3`   | `assetsmanager_prefix` | Objects prefix                            |
| `ASSETSMANAGER_TIMEOUT_S` | `300`         | `timeout_s`            | file lock timeout when downloading assets |

More settings can be passed in order to configure the driver itself.

## Storage driver settings

### AWS storage

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

### GCS storage

We use [google-cloud-storage](https://googleapis.dev/python/storage/latest/index.html).

| Environment variable             | Default value | Notes                 |
| -------------------------------- | ------------- | --------------------- |
| `GOOGLE_APPLICATION_CREDENTIALS` | None          | path to the JSON file |

By default, the GCS client use the credentials setup up on the machine.

If `GOOGLE_APPLICATION_CREDENTIALS` is provided, it should point to a local JSON service account file.

### Local storage

For simplicity, the full path of the bucket should be in `ASSETS_BUCKET_NAME`. For example, you can run `export ASSETS_BUCKET_NAME=$WORKING_DIR`.

## Prediction Service

`OVERRIDE_ASSETS_PREFIX` is used to set ModelLibrary `override_assetsmanager_prefix` setting
