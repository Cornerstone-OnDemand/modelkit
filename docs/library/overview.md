## `modelkit` Python library

The main objects in `modelkit` are `Model` and the `ModelLibrary`.

The `ModelLibrary` is able to instantiate and configure any `Model`
and keep track of it during execution. 

`Model` objects can then be requested via `ModelLibrary.get`,
 and used to make predictions via `Model`.

The ML logic is written in each `Model`'s `predict` functions, typically inside a module.

## Running tests

Make sure that you have your environment setup properly (see [Configuration](../configuration.md)) and run

```
pytest
```

In order to run the linters, etc: run `make lint`
