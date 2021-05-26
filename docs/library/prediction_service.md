The `ModelLibrary` is the primary object that provides predictions from  models.

## ModelLibrary

`ModelLibrary` objects can have a number of settings, passed as a dictionary
upon initialization `ModelLibrary(required_models = ..., settings = ...)`.
These parameters are exploited by the ModelLibrary directly
and set as the `service_settings` attribute of `Model` objects.

Main arguments:

- `models` a module, `Model` (or list of either) which is used to find configurations
  of the models to be loaded
- `configuration` allows you to provide an explicit configuration to override the ones present in the `Model.CONFIGURATIONS` attributes.
- `required_models` a list of models to load by the prediction service. This allows you to restrict the models that will actually be loaded onto memory. By default all models are loaded (`required_models=None`), pass the empty list to not load any models (or use the lazy mode). Names in this list have to be defined in the configurations of the models passed via `models`. You can pass a dictionary to override the asset for each model (see [here](developing_modelkit.md)).

Additionally, the `ModelLibrary` takes a `settings` keyword argument which allows you to provide advanced settings:

`Model` instance to be created for the required models. This is useful to download the assets
for example with TF serving
- `lazy_loading`: when True, this will cause the assets to be loaded lazily.
 This is useful for pyspark jobs with model object that are not serializable
- `enable_tf_serving`, `tf_serving_timeout_s`, `tf_serving_port`, `tf_serving_host`: Set
parameters related to the serving of TF models (see [here](tensorflow_models.md)).
- `assetsmanager_settings`: Parameters passed to the `assets.manager.AssetsManager`
- `override_storage_prefix`: Specify a side prefix from which the prediction service will try to download assets before falling back to classic storage_prefix.
 It is used to test new assets without having to push them in the main assets prefix (do not use in production).

## Lazy loading

Usually, all model assets are loaded as soon as the `ModelLibrary` is instantiated.
Sometimes this is not desirable, notably when using PySpark.

Thus, when `lazy_loading=True` the `ModelLibrary` tries to delay the loading and
deserialization of the assets as much as possible. You can also set this behavior by setting
`LAZY_LOADING=True` in your environment.

Specifically:

- When the `ModelLibrary` is instantiated nothing really happens: the `Model`
object is instantiated without deserializing the asset.
- When `ModelLibrary.get` is called the first time, the `Model`'s asset is
downloaded (via `ModelLibrary._load`) to a local directory and deserialized.

It is also possible to explicitly ask the `ModelLibrary` to load all `required_models` at
once by calling `ModelLibrary.preload`.

## Prediction caching

It is possible to use a redis caching mechanism to cache all calls to predict
for a `ModelLibrary` using the `enable_redis_cache`, `cache_host`, and
`cache_port` settings of the `LibrarySettings`. This has to be enabled for each model
by setting the `cache_predictions` model setting to `True`.

The caching works on individual items, before making a prediction with the methods
in the `Model` class, it will attempt to see if an available prediction is already
available in the cache.

Predictions in the cache are keyed by a hash of the passed item alongside the key
of the model (the key used in the configuration of the model).

When a prediction on a batch of items is requested, the `Model` will sieve through
each item and attempt to find cached predictions for each.
It will therefore only recompute predictions for the select items that do not appear
in the cache.
