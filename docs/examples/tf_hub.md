In this tutorial we will learn how to load a pre-trained Tensorflow saved model

We will use the [Universal Sentence Encoder](https://tfhub.dev/google/universal-sentence-encoder-multilingual/3) from tfhub as an example


# Download and extract

Fisrtly download the file `universal-sentence-encoder-multilingual_3.tar.gz` and extract it in a `asset_name/1` directory

In this tutorial we will use `/tmp/use/1`

`tar -xzvf universal-sentence-encoder-multilingual_3.tar.gz --directory /tmp/use/1`

this will create the following tree

```
use
└── 1
    ├── assets
    ├── saved_model.pb
    └── variables
        ├── variables.data-00000-of-00001
        └── variables.index
```

# Check the model configuration

In order to use `modelkit` to use the model we have to check the model configuation in order to exctract outputs informations (key name, layer name, shape and type) and the inputs key name

```
import tensorflow as tf
import tensorflow_text  # module need by use model
model = tf.saved_model.load("/tmp/use/1/")
print(model.signatures["serving_default"].output_dtypes)
print(model.signatures["serving_default"].output_shapes)
print(model.signatures["serving_default"].outputs)
print(model.signatures["serving_default"].inputs[0])

# Output:
# {'outputs': tf.float32}
# {'outputs': TensorShape([None, 512])}
# [<tf.Tensor 'Identity:0' shape=(None, 512) dtype=float32>]
# <tf.Tensor 'inputs:0' shape=(None,) dtype=string>
```

# Quick load with `modelkit`

We can now load the model by creating a `TensorflowModel` class and configuring it
with information we just get from the model

Note that we have to declare a "virtual" asset `"asset": "use"` to directly set an asset path `/tmp/use` (without the 1 directory)

```
import numpy as np
import tensorflow_text

import modelkit
from modelkit.core.models.tensorflow_model import TensorflowModel

class USEModel(TensorflowModel):
    CONFIGURATIONS = {
        "use": {
            "asset": "use",
            "model_settings": {
                "output_tensor_mapping": {"outputs": "Identity:0"},
                "output_shapes": {"outputs": (512,)},
                "output_dtypes": {"outputs": np.float32},
                "asset_path": "/tmp/use",
            },
        }
    }

```

and then we can test it using for example `load_model`

```
model = modelkit.load_model("use", models=USEModel)
model.predict({"inputs": "Hello world"})
# note that the "inputs" keyword is extracted from the previous model configuration
```

That's all !
We can start testing/using our model

```
from sklearn.metrics.pairwise import cosine_distances

sentence_1 = model.predict({"inputs": "My dog is quite calm today"})["outputs"]
sentence_2 = model.predict({"inputs": "Mon chien est assez calme aujourd'hui"})["outputs"]
sentence_3 = model.predict({"inputs": "It rains on my house"})["outputs"]
sentence_4 = model.predict({"inputs": "Il pleut sur ma maison"})["outputs"]

print(cosine_similarity([sentence_1, sentence_2, sentence_3, sentence_4]))
# output :
# [[1.         0.93083745 0.3172922  0.3379839 ]
#  [0.93083745 0.99999994 0.3522399  0.39009082]
#  [0.3172922  0.3522399  0.9999999  0.8444551 ]
#  [0.3379839  0.39009082 0.8444551  0.9999999 ]]

#  - sentence_1 close to sentence_2 (0.93)
#  - sentence_3 close to sentence_4 (0.84)
#  - other distances < 0.5

# => seems to work :-)
```

# Create an asset

Once we have test our model, we may want push and use it as an versioned asset

`./bin/cli.py assets new /tmp/use my_assets/use`

and then we can remove `asset_path` and add our `asset` name to our `TensorflowModel`

```
import numpy as np
import tensorflow_text

import modelkit
from modelkit.core.models.tensorflow_model import TensorflowModel

class USEModel(TensorflowModel):
    CONFIGURATIONS = {
        "use": {
            "asset": "my_assets/use:0.0",
            "model_settings": {
                "output_tensor_mapping": {"outputs": "Identity:0"},
                "output_shapes": {"outputs": (512,)},
                "output_dtypes": {"outputs": np.float32},
            },
        }
    }
```

and then we may use the library to load it

```
model_library = modelkit.ModelLibrary(
    required_models=["use"],
    models=USEModel,
)
model = model_library.get("use")
model.predict({"inputs": "Hello world"})
```

# Using tensorflow serving

Our model is directly compatible with our `tensorflow-serving` loading scripts

Let's say we have save our model in `modelkit/use.py` file

Generate the configuation

`./bin/cli.py tf-serving local-docker modelkit.use -r "use"`

it will create a config file `${MODELKIT_ASSETS_DIR}/config.config`

then we can start our `tf-serving` running

`docker run --name local-tf-serving -d -p 8500:8500 -p 8501:8501 -v ${MODELKIT_ASSETS_DIR}:/config -t tensorflow/serving --model_config_file=/config/config.config --rest_api_port=8501 --port=8500`

then we can try use use our model with `MODELKIT_TF_SERVING_ENABLE=1`, we should see the log line when loading the model

`[info     ] Connecting to tensorflow serving mode=rest model_name=use port=8501 tf_serving_host=localhost`
