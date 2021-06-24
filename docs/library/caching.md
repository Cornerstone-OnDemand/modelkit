
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
