class StorageDriverError(Exception):
    pass


class ObjectDoesNotExistError(StorageDriverError):
    def __init__(self, driver, bucket, object_name):
        super().__init__(
            f"Bucket {bucket} does not contain {object_name} (driver={driver})"
        )


class AssetsManagerError(Exception):
    pass


class AssetAlreadyExistsError(AssetsManagerError):
    def __init__(self, name):
        super().__init__(f"Asset {name} already exists, you should update it.")


class AssetDoesNotExistError(AssetsManagerError):
    def __init__(self, name):
        super().__init__(
            f"Asset {name} does not exist" "Use `push_new_asset` to create it."
        )


class AssetMajorVersionDoesNotExistError(AssetsManagerError):
    def __init__(self, name, major):
        super().__init__(
            f"Asset major version `{major}` for `{name}` does not exist."
            "Use `push_new_asset` to push a new major version of an asset."
        )


class InvalidAssetSpecError(AssetsManagerError):
    def __init__(self, spec):
        super().__init__(f"Invalid asset spec `{spec}`")


class InvalidVersionError(InvalidAssetSpecError):
    def __init__(self, version):
        super().__init__(f"Asset version `{version}` is not valid.")


class InvalidNameError(InvalidAssetSpecError):
    def __init__(self, name):
        super().__init__(f"Asset name `{name}` is not valid.")


class LocalAssetDoesNotExistError(AssetsManagerError):
    def __init__(self, name, version, local_versions):
        super().__init__(
            f"Asset version `{version}` for `{name}` does not exist locally. "
            f"Available asset versions: " + ", ".join(local_versions)
        )


class UnknownAssetsVersioningSystemError(AssetsManagerError):
    pass
