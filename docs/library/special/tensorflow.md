# Tensorflow models

`modelkit` provides different modes to use TF models, and makes it easy to switch between them.

- calling the TF model using the `tensorflow` module
- requesting predictions from TensorFlow Serving synchronously via a REST API
- requesting predictions from TensorFlow Serving asynchronously via a REST API
- requesting predictions from TensorFlow Serving synchronously via gRPC

## `TensorflowModel` class

All tensorflow based models should derive from the `TensorflowModel` class. This class provides a number of functions that help with loading/serving TF models.

At initialization time, a `TensorflowModel` has to be provided with definitions of the tensors predicted by the TF model:

- `output_tensor_mapping` a dict of arbitrary `key`s to tensor names describing the outputs.
- `output_tensor_shapes` and `output_dtypes` a dict of shapes and dtypes of these tensors.

!!! important
    Be careful that `_tensorflow_predict` returns a dict of `np.ndarray` of shape `(len(items),?)` when `_predict_batch` expects a list of `len(items)` dicts of `np.ndarray`.

## Other convenience methods

### Post processing

After the TF call, `_tensorflow_predict_*` returns a dict of `np.ndarray` of shape `(len(items),?)`.

These can be further manipulated by reimplementing the `TensorflowModel._post_processing` function, e.g. to reshape, change type, select a subset of features.

### Empty predictions

Oftentimes we manipulate the item before feeding it to TF, e.g. doing text cleaning or vectorization. This sometimes results in making the prediction trivial, in which case we need not bother calling TF with anything.

`modelkit` provides a built-in mechanism do deal with these "empty" examples, and the default implementation of `predict_batch` uses it.

To make use of it, override the `_is_empty` method:

```python
def _is_empty(self, item) -> bool:
    return item == ""
```

This will fill in missing values with zeroed arrays when empty strings are found, without calling TF.

To fill in values with another array, also override the `_generate_empty_prediction` method

```python
def _generate_empty_prediction(self) -> Dict[str, Any]:
    """Function used to fill in values when rebuilding predictions with the mask"""
    return {
        name: np.zeros((1,) + self.output_shapes[name], self.output_dtypes[name])
        for name in self.output_tensor_mapping
    }

```

### Keras model

The `TensorflowModel` class allows you to build an instance of keras.Model from the underlying saved tensorflow model via the method `get_keras_model()`. 

## TF Serving

`modelkit` provides an easy way to query Tensorflow models served via TF Serving. When TF serving is configured, the TF models are not run in the main process, but queried.

### Running TF serving container locally

In order to run a TF Serving docker locally, one first needs to download the models and write a configuration file.

This can be achieved by

```sh
modelkit tf-serving local-docker --models [PACKAGE]
```

The CLI creates a configuration file for tensorflow serving, with the model locations refered to _relative to the container file system_. As a result, the TF serving container will expect that the `MODELKIT_ASSETS_DIR` is bound to the `/config` directory inside the container.

Specifically, the CLI:

- Instantiates a `ModelLibrary` with all configured models in `PACKAGE`
- Downloads all necessary assets in the `MODELKIT_ASSETS_DIR`
- writes a configuration file under the local `MODELKIT_ASSETS_DIR` with all TF models that are configured

The container can then be started by pointing TF serving to the generated configuration file `--model_config_file=/config/config.config`:

```sh
docker run \
        --name local-tf-serving \
        -d \
        -p 8500:8500 -p 8501:8501 \
        -v ${MODELKIT_ASSETS_DIR}:/config \
        -t tensorflow/serving \
        --model_config_file=/config/config.config\
        --rest_api_port=8501\
        --port=8500
```

See also:

- [the CLI documentation](../../cli.md).
- the Tensorflow serving [documentation](https://www.tensorflow.org/tfx/serving/docker)
- the Tensorflow serving [github](https://github.com/tensorflow/serving/tree/master/tensorflow_serving)

### Internal TF serving settings

Several environment variables control how `modelkit` requests predictions from TF serving.

- `MODELKIT_TF_SERVING_ENABLE`: Controls whether to use TF serving or use TF locally as a lib
- `MODELKIT_TF_SERVING_HOST`: Host to connect to to request TF predictions
- `MODELKIT_TF_SERVING_PORT`: Port to connect to to request TF predictions
- `MODELKIT_TF_SERVING_MODE`: Can be `grpc` (with `grpc`) or `rest` (with `requests` for `TensorflowModel`, or with `aiohttp` for `AsyncTensorflowModel`)
- `MODELKIT_TF_SERVING_ATTEMPTS`: number of attempts to wait for TF serving response

All of these parameters can be set programmatically (and passed to the `ModelLibrary`'s settings):

```python
lib_serving_grpc = ModelLibrary(
    required_models=...,
    settings=LibrarySettings(
        tf_serving={
            "enable": True,
            "port": 8500,
            "mode": "grpc",
            "host": "localhost",
        }
    ),
    models=...,
)
```

### Using TF Serving during tests

`modelkit` provides a fixture to run TF serving during testing:

```python
@pytest.fixture(scope="session")
def tf_serving():
    lib = ModelLibrary(models=..., settings={"lazy_loading": True})
    yield tf_serving_fixture(request, lib, tf_version="2.8.0")
```

This will configure and run TF serving during the test session, provided `docker` is present.
