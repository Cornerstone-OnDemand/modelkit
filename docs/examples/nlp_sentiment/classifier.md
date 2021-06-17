In this section, we will implement a sentiment classifier with Keras, using the components we have been developping so far.

## Data preparation

We will reuse the `read_dataset` function, in addition to a few other helper functions which will continue taking advantage of generators to avoid loading up the entire dataset into memory:

- `alternate(f, g)`: to yield items alternatively between the f and g generators
- `alternate_labels()`: to yield 1 and 0, alternatively, in sync with the previous `alternate` function

```python
import glob
import os

from typing import Generator, Any

def read_dataset(path: str) -> Generator[str, None, None]:
    for review in glob.glob(os.path.join(path, "*.txt")):
        with open(review, 'r', encoding='utf-8') as f:
            yield f.read()

def alternate(
    f: Generator[Any, Any, Any], g: Generator[Any, Any, Any]
) -> Generator[Any, None, None]:
    while True:
        try:
            yield next(f)
            yield next(g)
        except StopIteration:
            break

def alternate_labels() -> Generator[int, None, None]:
    while True:
        yield 1
        yield 0

```

Let's plug these pipes together so that to efficiently read and process the IMDB reviews dataset for our next Keras classifier, leveraging the Tokenizer and Vectorizer we implemented in the first two sections:

```python
def process(path, tokenizer, vectorizer, length, batch_size):
    # read the positive sentiment reviews dataset
    positive_dataset = read_dataset(os.path.join(path, "pos"))
    # read the negative sentiment reviews dataset
    negative_dataset = read_dataset(os.path.join(path, "neg"))
    # alternate between positives and negatives examples
    dataset = alternate(positive_dataset, negative_dataset)
    # generate labels in sync with the previous generator: 1 for positive examples, 0 for negative ones
    labels = alternate_labels()

    # tokenize the reviews using our Tokenizer Model
    tokenized_dataset = tokenizer.predict_gen(dataset, batch_size=batch_size)
    # vectorize the reviews using our Vectorizer Model
    vectorized_dataset = vectorizer.predict_gen(
        tokenized_dataset, length=length, batch_size=batch_size
    )
    # yield (review, label) tuples for Keras
    yield from zip(vectorized_dataset, labels)
```

Let's try it out on the first examples:

```python

i = 0
for review, label in process(
    os.path.join("aclImdb", "train"),
    Tokenizer(),
    Vectorizer(),
    length=64,
    batch_size=64,
):
    print(review, label)
    i += 1
    if i >= 10:
        break
```

### Model library

So far, we have instantiated `Tokenizer` and `Vectorizer` classes as standard objects. Modelkit provides a simpler and more powerful way to instantiate `Models`, the library: `modelkit.ModelLibrary`.

The purpose of the `ModelLibrary` is to have a single way to load any of the models that are defined, any way you decide to keep them organized.

With a library `ModelLibrary` you can

- fetch models by their configuration key using `ModelLibrary.get` while ensuring that models are only loaded once
- use prediction caching: [Prediction Caching](../../library/model_library.md#prediction-caching)
- use lazy loading for models: [Lazy Loading](../../library/model_library.md#lazy-loading)
- override model parameters: [Settings](../../library/model_library.md#modellibrary)

Although we will not cover all of these features here, let's see how we can take advantage of the `ModelLibrary` with our previous work.

Let us define a model library, it can take the clases of models as input:

```python
import modelkit

... # define Vectorizer and Tokenizer classes

model_library = modelkit.ModelLibrary(models=[Vectorizer, Tokenizer])
tokenizer = model_library.get("imdb_tokenizer")
vectorizer = model_library.get("imdb_vectorizer")

```

Or, alternatively use the modules they are present in:

```python
import module_with_models

model_library = modelkit.ModelLibrary(models=module_with_models)
```

This method is the preferred method, because it encourages you to adopt a package-like organisation of your `Models` (see [Organizing Models](../../library/organizing.md))

### Using models to create a TF.Dataset

Now that we know how to reach out models, let us use them to create a `TF Dataset` from our data processing generators:

```python hl_lines="11 12 26 27"
import os
import tensorflow as tf

BATCH_SIZE = 64
LENGTH = 64

training_set = (
    tf.data.Dataset.from_generator(
        lambda: process(
            os.path.join("aclImdb", "train"),
            tokenizer.predict,
            vectorizer.predict,
            length=LENGTH,
            batch_size=BATCH_SIZE,
        ),
        output_types=(tf.int16, tf.int16),
    )
    .batch(BATCH_SIZE)
    .repeat()
    .prefetch(1)
)
validation_set = (
    tf.data.Dataset.from_generator(
        lambda: process(
            os.path.join("aclImdb", "test"),
            tokenizer.predict,
            vectorizer.predict,
            length=LENGTH,
            batch_size=BATCH_SIZE,
        ),
        output_types=(tf.int16, tf.int16),
    )
    .batch(BATCH_SIZE)
    .repeat()
    .prefetch(1)
)


```

## Training a Keras model

Let's train a basic Keras classifier to predict whether an IMDB review is positive or negative, and save it to disk.

```python
import tensorflow as tf

model = tf.keras.Sequential(
    [
        tf.keras.layers.Embedding(
            input_dim=len(vectorizer.vocabulary) + 2, output_dim=64, input_length=LENGTH
        ),
        tf.keras.layers.Lambda(lambda x: tf.reduce_sum(x, axis=1)),
        tf.keras.layers.Dense(1, activation="sigmoid"),
    ]
)
model.compile(
    tf.keras.optimizers.Adam(0.001),
    loss=tf.keras.losses.BinaryCrossentropy(),
    metrics=[tf.keras.metrics.binary_accuracy],
)
model.build()
model.fit(
    training_set,
    validation_data=validation_set,
    epochs=10,
    steps_per_epoch=100,
    validation_steps=10,
)
model.save(
    "imdb_model.h5", include_optimizer=False, save_format="h5", save_traces=False
)
```

### Classifier Model

Voilà ! As we already did for the Vectorizer, we will embed the just-saved `imdb_model.h5` in a basic Modelkit `Model` which we will further upgrade in the next section.

```python
import modelkit
import tensorflow as tf

from typing import List


class Classifier(modelkit.Model[List[int], float]):
    CONFIGURATIONS = {"imdb_classifier": {"asset": "imdb_model.h5"}}

    def _load(self):
        self.model = tf.keras.models.load_model(self.asset_path)

    def _predict_batch(self, vectorized_reviews):
        return self.model.predict(vectorized_reviews)
```

Much like we did for the `Vectorizer`, the `Classifier` model has a `imdb_classifier` configuration with an asset pointing to the `imdb_model.h5`.

We also benefit from Keras' `predict` ability to batch predictions in our `_predict_batch` method.

## End-to-end prediction

To summarize, here is how we would want to chain our `Tokenizer`, `Vectorizer` and `Classifier`:

```python
import modelkit

library = modelkit.ModelLibrary(models=[Tokenizer, Vectorizer, Classifier])
tokenizer = library.get("imdb_tokenizer")
vectorizer = library.get("imdb_vectorizer")
classifier = library.get("imdb_classifier")

review = "I freaking love this movie, the main character is so cool !"

tokenized_review = tokenizer(review)  # or tokenizer.predict
vectorized_review = vectorizer(tokenized_review)  # or vectorizer.predict
prediction = classifier(vectorized_review)  # or classifier.predict
```

In the next (and final) section, we will see how `modelkit` can be used to perform this operation in a single `Model`.