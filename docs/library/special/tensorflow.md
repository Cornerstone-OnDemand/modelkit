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
- `output_tensor_shapes` and `output_tensor_dtypes` a dict of shapes and dtypes of these tensors.

Typically, inside a `_predict_batch`, one would do something like:

```python
def _predict_batch(self, items):
    data = await self._tensorflow_predict(
            {
                key: np.stack([item[key] for item in items], axis=0)
                for key in items[0]
            }
        )
    # ...
    return [
            {
                key: data[key][k]
                for key in self.output_tensor_mapping
            }
            for k in range(len(items))
        ]
```

!!! important
    Be careful that `_tensorflow_predict` returns a dict of `np.ndarray` of shape `(len(items),?)` when `_predict_batch` expects a list of `len(items)` dicts of `np.ndarray`.

## Other convenience methods

### Post processing

After the TF call, `_tensorflow_predict_*` returns a dict of `np.ndarray` of shape `(len(items),?)`.

These can be further manipulated by reimplementing the `TensorflowModel._post_processing` function, e.g. to reshape, change type, select a subset of features.

### Empty predictions

Oftentimes we manipulate the item before feeding it to TF, e.g. doing text cleaning or vectorization. This sometimes results in making the prediction trivial.

In this case we use the following pattern, wherein we leverage the method `TensorflowModel._rebuild_predictions_with_mask`:

```python
def _predict_batch(
    self, items: List[Dict[str, str]], **kwargs
) -> List[Tuple[np.ndarray, List[str]]]:
    treated_items = self.treat(items)

    # Some of them can be None / empty, let's filter them out before prediction
    mask = [x is not None and np.count_nonzero(x) > 0 for x in treated_items]
    results = []
    if any(mask):
        items_to_predict = np.concatenate(list(compress(treated_items, mask)))
        results = await self._tensorflow_predict(
            {"input_tensor": items_to_predict}
        )
    # Merge the just-computed predictions with empty vectors for empty items
    # Making sure everything is well-aligned
    return self._rebuild_predictions_with_mask(mask, results)
```

Notably, `TensorflowModel._rebuild_predictions_with_mask` uses `TensorflowModel._generate_empty_prediction` which returns the prediction expected for empty items

## TF Serving

`modelkit` provides an easy way to query Tensorflow models served via TF Serving. When TF serving is configured, the TF models are not run in the main process, but queried.

### Running TF serving container locally

In order to run a TF Serving docker locally, one first needs to download the models and write a configuration file.

This can be achieved by

```sh
modelkit tf-serving local-docker --models [PACKAGE]
```

The CLI creates a configuration file for tensorflow serving, with the model locations refered to _relative to the container file system_. As a result, the TF serving container will expect that the `WORKING_DIR` is bound to the `/config` directory inside the container.

Specifically, the CLI:

- Instantiates a `ModelLibrary` with all configured models in `PACKAGE`
- Downloads all necessary assets in the `WORKING_DIR`
- writes a configuration file under the local `WORKING_DIR` with all TF models that are configured

The container can then be started by pointing TF serving to the generated configuration file `--model_config_file=/config/config.config`:

```sh
docker run \
        --name local-tf-serving \
        -d \
        -p 8500:8500 -p 8501:8501 \
        -v ${WORKING_DIR}:/config \
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

- `ENABLE_TF_SERVING`: Controls whether to use TF serving or use TF locally as a lib
- `TF_SERVING_HOST`: Host to connect to to request TF predictions
- `TF_SERVING_PORT`: Port to connect to to request TF predictions
- `TF_SERVING_MODE`: Can be `grpc` (with `grpc`) or `rest` (with `requests` for `TensorflowModel`, or with `aiohttp` for `AsyncTensorflowModel`)
- `TF_SERVING_TIMEOUT_S`: timeout to wait for the first TF serving response

All of these parameters can be set programmatically (and passed to the `ModelLibrary`'s settings):

```python
svc_serving_grpc = ModelLibrary(
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
    yield tf_serving_fixture(request, lib)
```

This will configure and run TF serving during the test session, provided `docker` is present.
