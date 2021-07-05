# `modelkit` CLI

## Models description

### Describe

This CLI prints out all relevant information on a 
given `modelkit` model repository:
```sh
modelkit describe [PACKAGE] [--required-models ...]
```
### Assets listing

This CLI will show all necessary assets to run models
```sh
modelkit list-assets [PACKAGE] [--required-models ...]
```
### Assets download

This CLI will download all necessary assets to run models to the current `MODELKIT_ASSETS_DIR`
```sh
modelkit list-assets [PACKAGE] [--required-models ...]
```

Once this is done, you can run the models without enabling a storage provider.
### Dependencies graph

This CLI will create a .DOT file with a graph of all models,
their assets and model dependencies.
```sh
modelkit dependencies-graph [PACKAGE] [--required-models ...]
```
This requires [graphviz](https://graphviz.org/) for the graph layout. 


## Predictions

### batch

This CLI will treat a given JSONL file, with one item per line and write the output of a 
model as another JSONL file, using multiple processes for speed

```sh
modelkit batch MODEL_NAME DATA_IN DATA_OUT [--models PACKAGE] [--processes N_PROCESSES] [--unordered]
```

Where:
- `--models` to tell it where to find the model
- `--processes` allows you to define the number of processes (defaults to all CPUs)
- `--unordered` does not preserve the order of outputs (as with `imap_unordered`), which may be faster

## Benchmarking

### Memory benchmark

This CLI attempts to measure the memory consumption 
of a set of `modelkit` models:
```sh
modelkit memory [PACKAGE] [--required-models ...]
```

### Time

This CLI accepts a model and item, and will time the prediction
```sh
modelkit time MODEL_NAME EXAMPLE_ITEM --models PACKAGE
```

## Serving

`modelkit` provides a single CLI to run a local `FastAPI` server with
all loaded models mounted as endpoints:
```sh
modelkit serve PACKAGE [--required-models ...]
```
This is useful in order to inspect the swagger.

!!! important
    Note that models whose payloads are not serializable will
    not be exposed, this is true in particular of numpy arrays

## Assets management

To list all assets:
```sh
$ modelkit assets list
```

To create a new asset:
```sh
$ modelkit assets new /path/to/asset asset_category/asset_name
```

To update an asset's minor version:

```sh
$ modelkit assets update /path/to/asset asset_category/asset_name
```

To push a new major version:
```sh
$ modelkit assets update /path/to/asset asset_category/asset_name --bump-major
```

## TF serving

To configure models from a package to be run in TF serving:
```sh
modelkit tf-serving local-docker --models [PACKAGE]
```

This will write a configuration file with relative paths to the model files. This is meant to be used by mounting the `MODELKIT_ASSETS_DIR` in the container under the path `/config`.

Other options include:
- `local-process` To create a config file with absolute paths to the assets under `MODELKIT_ASSETS_DIR`
- `remote` which will use whichever remote paths are found for the assets (i.e. as configured by the `MODELKIT_STORAGE_PROVIDER`)
