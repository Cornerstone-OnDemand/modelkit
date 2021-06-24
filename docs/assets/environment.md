# Environment

## Model library

The only necessary environment variable to set to use `modelkit` is the assets directory `MODELKIT_ASSETS_DIR` it has to be a valid local directory.

## AssetsManager settings

The parameters necessary to instantiate an `AssetsManager` can all be read from environment variables, or provided when initializing the `AssetsManager`.

| Environment variable | Default value | Parameter | Notes |
| --- | --- | --- | --- |
| `MODELKIT_STORAGE_PROVIDER` | `gcs` | `storage_provider` | `gcs` (default), `s3` or `local` |
| `MODELKIT_STORAGE_BUCKET` | None | `bucket` | Bucket in which data is stored |
| `MODELKIT_STORAGE_PREFIX` | `modelkit-assets` | `storage_prefix` | Objects prefix |
| `MODELKIT_STORAGE_TIMEOUT_S` | `300` | `timeout_s` | max time when retrying storage downloads |
| `MODELKIT_ASSETS_TIMEOUT_S` | `10` | `timeout` | file lock timeout when downloading assets |

More settings can be passed in order to configure the driver itself, see the [storage provider documentation for more information](storage_provider.md)
