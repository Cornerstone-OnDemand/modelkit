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
### Dependencies graph

This CLI will create a .DOT file with a graph of all models,
their assets and model dependencies.
```sh
modelkit dependencies-graph [PACKAGE] [--required-models ...]
```
This requires [graphviz](https://graphviz.org/) for the graph layout. 


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

!!! warning
    Note that models whose payloads are not serializable will
    not be exposed, this is true in particular of numpy arrays