# Command line interfaces

## Generic CLIs

### General purpose predict

This prompt accept JSON items and prints predictions.
```sh
bin/predict.py model_name
```

### Benchmarking CLI

We expose a number of maintenance/benchmarking CLI in `bin/benchmark.py`

#### Memory consumption

Benchmark the memory consumption of a `ModelLibrary` with all models
```sh
bin/benchmark.py
```

#### Model dependency graph

Create a [dot](https://en.wikipedia.org/wiki/DOT_(graph_description_language)) graph dependency file of models' dependencies and required assets with:
```sh
bin/benchmark.py dependency-graph --model model_1 --model model_2
```

Or, for all models
```sh
bin/benchmark.py dependency-graph --all
```

To produce a neat PNG file from the `dependencies.dot` file use:
```sh
neato -Tpng dependencies.dot > dependency-graph-v1.png
```

#### List assets

List the assets necessary for a given set of models
```sh
bin/benchmark.py assets --model model_1 --model model_2
```

Or, for all models
```sh
bin/benchmark.py assets --all
```



### TF Serving CLIs

#### Local deployment CLI

These CLIs download the models and create the directory structure and configuration file necessary for the TF serving Docker containers.

```sh
bin/tf_serving.py configure [local-docker|local-process|remote-gcs|remote-s3] SERVICE_NAME [--verbose]
```

Where `SERVICE_NAME` is a key of the dictionary `modelkit.models.config.TF_SERVING_MODELS`.

In `local-docker` mode this will write a configuration file to `${WORKING_DIR}/modelkit-assets/SERVICE_NAME.config`, usable with a docker container whose `/config` folder points to `${WORKING_DIR}/modelkit-assets`.

In `local-process` mode this will write a configuration file to `${WORKING_DIR}/modelkit-assets/SERVICE_NAME.config`, usable with the TF serving process (that is, will local paths hardcoded in the configuration, this is used in the CI and not recommended).

In `remote-s3` mode this won't upload any data, but with `--verbose` this will print the configuration that you can copy/paste in the src/deploy/tensorflow/tensorflow.config.template file in a given PipelineKit project.

#### Run the container

```sh
bin/run_tfserving.sh SERVICE_NAME
```

Starts the TF serving container given the exported models in `${WORKING_DIR}/tfserving-models` for the given `SERVICE_NAME` (pointing to the right config file).

!!! info
    Don't forget to
    ```
    docker rm -f local-tf-serving
    ```
    when you are done.
