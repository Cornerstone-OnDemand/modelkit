

Usually, all model assets are loaded as soon as the `ModelLibrary` is instantiated.
Sometimes this is not desirable, notably when using PySpark.

Thus, when `lazy_loading=True` the `ModelLibrary` tries to delay the loading and
deserialization of the assets as much as possible. You can also set this behavior by setting
`MODELKIT_LAZY_LOADING=True` in your environment.

Specifically:

- When the `ModelLibrary` is instantiated nothing really happens: the `Model`
object is instantiated without deserializing the asset.
- When `ModelLibrary.get` is called the first time, the `Model`'s asset is
downloaded (via `ModelLibrary._load`) to a local directory and deserialized.

It is also possible to explicitly ask the `ModelLibrary` to load all `required_models` at
once by calling `ModelLibrary.preload`.


