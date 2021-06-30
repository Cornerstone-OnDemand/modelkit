The `ModelLibrary` is the primary object that provides predictions from  models.


`ModelLibrary` objects can have a number of settings, passed as a dictionary
upon initialization `ModelLibrary(required_models = ..., settings = ...)`.
These parameters are exploited by the ModelLibrary directly
and set as the `service_settings` attribute of `Model` objects.

Main arguments:

- `models` a module, `Model` (or list of either) which is used to find configurations
  of the models to be loaded
- `configuration` allows you to provide an explicit configuration to override the ones present in the `Model.CONFIGURATIONS` attributes.
- `required_models` a list of models to load by the library. This allows you to restrict the models that will actually be loaded into memory. By default all models from `models` are loaded (`required_models=None`), pass the empty list to not load any models (or use the lazy mode). Names in this list have to be defined in the configurations of the models passed via `models`. You can pass a dictionary to override the asset for each model.

Additionally, the `ModelLibrary` takes a `settings` keyword argument which allows you to provide advanced settings:

`Model` instance to be created for the required models. This is useful to download the assets for example with TF serving

- `lazy_loading`: when True, this will cause the assets to be loaded lazily.
 This is useful for pyspark jobs with model object that are not serializable
- `enable_tf_serving`, `tf_serving_port`, `tf_serving_host`: Set
parameters related to the serving of TF models (see [here](special/tensorflow.md)).
- `assetsmanager_settings`: Parameters passed to the `assets.manager.AssetsManager`
- `override_storage_prefix`: Specify a side prefix from which the prediction service will try to download assets before falling back to classic storage_prefix. It is used to test new assets without having to push them in the main assets prefix (do not use in production).
