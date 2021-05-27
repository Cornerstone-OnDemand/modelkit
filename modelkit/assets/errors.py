class StorageDriverError(Exception):
    pass


class BucketDoesNotExistError(StorageDriverError):
    def __init__(self, driver, bucket):
        super().__init__(f"Bucket {bucket} does not exist (driver={driver})")


class ObjectDoesNotExistError(StorageDriverError):
    def __init__(self, driver, bucket, object_name):
        super().__init__(
            f"Bucket {bucket} does not contain {object_name} (driver={driver})"
        )


class AssetsManagerError(Exception):
    pass


class AssetAlreadyExistsError(AssetsManagerError):
    def __init__(self, name):
        super().__init__(f"Assert {name} already exists, you should update it.")


class AssetDoesNotExistError(AssetsManagerError):
    def __init__(self, name):
        super().__init__(
            f"Assert {name} does not exist" "Use `push_new_asset` to create it."
        )


class AssetMajorVersionDoesNotExistError(AssetsManagerError):
    def __init__(self, name, major):
        super().__init__(
            f"Assert major version `{major}` for `{name}` does not exist."
            "Use `push_new_asset` to push a new major version of an asset."
        )


class AssetMajorVersionAlreadyExistsError(AssetsManagerError):
    def __init__(self, name, major):
        super().__init__(
            f"Assert major version `{major}` for `{name}` already exists."
            "Use `update` to push a new minor version of an asset."
        )


class InvalidAssetSpecError(AssetsManagerError):
    def __init__(self, spec):
        super().__init__(f"Invalid asset spec `{spec}`")


class LocalAssetVersionDoesNotExistError(AssetsManagerError):
    def __init__(self, name, major, minor):
        super().__init__(
            f"Asset major version `{major}.{minor}` for `{name}` does not exist."
            "Use `push_new_asset` to push a new major version of an asset."
        )


class LocalAssetDoesNotExistError(AssetsManagerError):
    def __init__(self, name, major, minor, local_versions):
        super().__init__(
            f"Asset version `{major}.{minor}` for `{name}` does not exist locally. "
            f"Available asset versions: " + ", ".join(local_versions)
        )
