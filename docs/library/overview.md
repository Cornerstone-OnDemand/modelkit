## `modelkit` Python library

The main objects in `modelkit` are `Model` and the `ModelLibrary`.

Put simply, a `ModelLibrary` is used to fetch any `Model`
and keep track of it during execution, the service will fetch any serialized assets, and load the object in memory.

`Model` objects can then be requested via `ModelLibrary.get`,
 and used to make predictions via `Model.predict`.

The ML logic is written in each `Model`'s `predict` functions, typically inside a submodule of `modelkit.models`.

## Running tests

Make sure that you have your environment setup properly (see [Configuration](../configuration.md)) and run

```
pytest
```

In order to run the linters, etc: run `make lint`
