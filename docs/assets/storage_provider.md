In order to take advantage of remote asset storage, you have to configure your environment to use the right **storage provider**.

This is generally done by means of environment variables, and currently supports object stores on S3 (e.g. AWS, or minio) or GCS.

The first thing you will need is a local directory in which assets will be retrieved and stored. This is best set in an environment variable `MODELKIT_ASSETS_DIR` which has to point to an existing directory.

## Remote storage paths

You will need a remote object store, as identified by a bucket, and `modelkit` will store all objects under a given prefix. 

These are controlled by the following environment variables

- `MODELKIT_STORAGE_BUCKET` the name of the buket
- `MODELKIT_STORAGE_PREFIX` the prefix of all `modelkit` objects in the bucket

### Permissions

You will need to have credentials present with permissions.

#### At runtime 

This is typically the case of running services, they need read access to all the objects in the bucket under the storage prefix.


#### For developers

Developers may additionally need to be able to push new assets and or update existing assets, which requires them to be able to create and update certain objects.

## Using different providers

The flavor of the remote store that is used depends on the `MODELKIT_STORAGE_PROVIDER` environment variables

### Using AWS S3 storage

Use `MODELKIT_STORAGE_PROVIDER=s3` to connect to S3 storage.

We use [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) under the hood.

The authentication information here is passed to the `boto3.client` object:

| Environment variable    | boto3.client argument   |
| ----------------------- | ----------------------- |
| `AWS_ACCESS_KEY_ID`     | `aws_access_key_id`     |
| `AWS_SECRET_ACCESS_KEY` | `aws_secret_access_key` |
| `AWS_SESSION_TOKEN`     | `aws_session_token`     |
| `AWS_DEFAULT_REGION`    | `region_name`           |
| `S3_ENDPOINT`           | `endpoint_url`          |

Typically, if you use AWS: having `AWS_DEFAULT_PROFILE`, `AWS_DEFAULT_REGION` and valid credentials in `~/.aws` is enough.

S3 storage driver is compatible with KMS encrypted s3 volumes.
Use `AWS_KMS_KEY_ID` environment variable to set your key and be able to upload files to such volume.

### GCS storage

Use `MODELKIT_STORAGE_PROVIDER=gcs` to connect to GCS storage.

We use [google-cloud-storage](https://googleapis.dev/python/storage/latest/index.html).

| Environment variable             | Default value | Notes                 |
| -------------------------------- | ------------- | --------------------- |
| `GOOGLE_APPLICATION_CREDENTIALS` | None          | path to the JSON file |

By default, the GCS client use the credentials setup up on the machine.

If `GOOGLE_APPLICATION_CREDENTIALS` is provided, it should point to a local JSON service account file, which we use to instantiate the client with `google.cloud.storage.Client.from_service_account_json`

### Using Azure blob storage

Use `MODELKIT_STORAGE_PROVIDER=az` to connect to Azure blob storage.

We use [azure-storage-blobl](https://docs.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python) under the hood.

The client is created by passing the authentication information to `BlobServiceClient.from_connection_string`:

| Environment variable    | Note   |
| ----------------------- | ----------------------- |
| `AZURE_STORAGE_CONNECTION_STRING`     | azure connection string     |


### `local` mode

Use `MODELKIT_STORAGE_PROVIDER=local` to treat a local folder as a remote source.

Assets will be downloaded from this folder to the configured asset dir.

If you would like to run on already downloaded assets.

| Environment variable             | Notes                 |
| -------------------------------- | --------------------- |
| `MODELKIT_STORAGE_BUCKET`        | path to the local folder |
| `MODELKIT_STORAGE_PREFIX`        | sub directory where assets are fetched from |

### Pre-downloaded mode

Use `MODELKIT_STORAGE_PROVIDER=` to use only assets available in assets dir.

This can be used for local development or for deploying assets in read-only artifacts.


## Other options


If you would like us to support other means of remote storage, do feel free to request it by posting [an issue](https://github.com/Cornerstone-OnDemand/modelkit/issues)!