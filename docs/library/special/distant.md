# Tensorflow models

`modelkit` provides different modes to use TF models, and makes it relatively easy to
switch between them.

-   calling the TF model using the `tensorflow` module
-   requesting predictions from TensorFlow Serving synchronously via a REST API
-   requesting predictions from TensorFlow Serving asynchronously via a REST API
-   requesting predictions from TensorFlow Serving synchronously via gRPC

# TF Serving

## Running a TF serving container locally

In order to run a TF Serving docker locally, one first needs to download the models and write a configuration file.

This can be achieved by `bin/tf_serving.py configure local-docker [SERVICE]`, which will write the configuration file under the local `WORKING_DIR`.

`SERVICE` refers to a key of the `modelkit.models.config.TF_SERVING_MODELS`, so essentially describes different subsets of the models that use TF serving. Possible keys are `modelkit` or `dataplayground`.

The bash script `bin/run_tf_serving.sh` then runs the docker container exposing both the REST and gRPC endpoints.

Also see [the CLI documentation](../../cli.md).

## Details

The CLI `bin/tf_serving.py configure local-docker` creates a configuration file for tensorflow serving, with the model locations refered to _relative to the container file system_. As a result, the TF serving container will expect that the `WORKING_DIR/modelkit-assets` is bound to the `/config` directory inside the container.

The container can then be started by pointing TF serving to the
generated configuration file `--model_config_file=/config/modelkit.config`.
This is already achieved by the `bin/run_tfserving.sh` CLI.

See also:

-   the Tensorflow serving [documentation](https://www.tensorflow.org/tfx/serving/docker)
-   the Tensorflow serving [github](https://github.com/tensorflow/serving/tree/master/tensorflow_serving)

# Internal TF serving settings

Several parameters control how `modelkit` requests predictions from TF serving.

-   `enable_tf_serving`: Controls wether to use TF serving or use TF locally as a lib
-   `tf_serving_host`: Host to connect to to request TF predictions
-   `tf_serving_port`: Port to connect to to request TF predictions
-   `tf_serving_mode`: Can be `grpc` (with `grpc`) or `rest` (with `requests`)
    or `rest-async` (with `aiohttp`)
-   `tf_serving_timeout_s`: timeout to wait for the first TF serving response

All of these parameters can be set programmatically (and passed to the `ModelLibrary`'s settings),
or they are fetched from environment variables (which take precedence), in which case they
should be uppercased.

## `TensorflowModel` class

All tensorflow based models should derive from the `TensorflowModel` class. This class
provides a number of functions that help with loading/serving TF models.

At initialization time, a `TensorflowModel` has to be provided with definitions of the
tensors predicted by the TF model:

-   `output_tensor_mapping` a dict of arbitrary `key`s to tensor names describing the
    outputs.
-   `output_tensor_shapes` and `output_tensor_dtypes` a dict of shapes and dtypes of these
    tensors.

Typically, inside a `_predict_batch`, one would do something like:

```python
async def _predict_batch(self, items):
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
    Be careful that `_tensorflow_predict` returns a dict of `np.ndarray` of shape `(len(items),?)`
    when `_predict_batch` expects a list of `len(items)` dicts of `np.ndarray`.

## Other methods to re-implement

### Post processing

After the TF call, `_tensorflow_predict_*` returns a dict of `np.ndarray` of shape `(len(items),?)`.

These can be further manipulated by reimplementing the
`TensorflowModel._post_processing` function, e.g. to reshape, change type, select a subset of features.

### Empty predictions

Oftentimes we manipulate the item before feeding it to TF, e.g. doing text cleaning or
vectorization. This sometimes results in making the prediction trivial. 

In this case we use the following pattern, wherein we leverage the method
`TensorflowModel._rebuild_predictions_with_mask`:

```python
async def _predict_batch(
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

Notably, `TensorflowModel._rebuild_predictions_with_mask` uses
`TensorflowModel._generate_empty_prediction` which returns the prediction expected
for empty items

# TF Serving during tests

During tests locally on an OSX machine, TF serving is run locally using the TF serving docker and the `docker` python library (see the `tf_serving` fixture in `tests/conftest.py`).

On the CI/CD pipelines, `docker` is not available, so we run `tensorflow-model-server` directly after installing it via `apt`.
