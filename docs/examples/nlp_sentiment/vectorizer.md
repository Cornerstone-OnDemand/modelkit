In this section, we will fit and implement a custom text vectorizer based on the [sentiment analysis IMDB dataset](https://ai.stanford.edu/~amaas/data/sentiment/).

It will be the opportunity to go through modelkit's assets management basics, learn how to fetch artifacts, and get deeper into its API.

## Installation

First, let's download the IMDB reviews dataset:

```
# download the remote archive
curl https://ai.stanford.edu/~amaas/data/sentiment/aclImdb_v1.tar.gz --output imdb.tar.gz
# untar it
tar -xvf imdb.tar.gz
# remove the unsupervised directory we will not be using
rm -rf aclImdb/train/unsup
```

The different files consist in text reviews left by IMDB users, each file corresponding to one review.

The dataset is organized with train and test directories, containing positive and negative examples in subfolders corresponding to the target classes.

## Creating an asset file
### Fitting

First thing first, let's define a helper function to read through the training set.

We will only be using generators to avoid loading the entire dataset in memory, (and later use `Model.predict_gen` to process them).

```python 
import glob
from typing import Generator

def read_dataset(path: str) -> Generator[str, None, None]:
    for review in glob.glob(os.path.join(path, "*.txt")):
        with open(review, 'r', encoding='utf-8') as f:
            yield f.read()
```

We need to tokenize our dataset before fitting a [Scikit-Learn](https://scikit-learn.org/stable/) `TfidfVectorizer`,

Although sklearn includes a tokenizer, we will be using the one we implemented in the first section.

```python
import itertools
import os

training_set = itertools.chain(
    read_dataset(os.path.join("aclImdb", "train", "pos")),
    read_dataset(os.path.join("aclImdb", "train", "neg")),
)
tokenized_set = Tokenizer().predict_gen(training_set)
```

By using generators and the `predict_gen` method, we can to read huge texts corpora without filling up our memory.

Each review will be tokenized one by one, but as we discussed we can also speed up execution by setting a `batch_size` greater than one, to process these reviews batch by batch.

```python
# here, an example with a 64 batch size
tokenized_set = Tokenizer().predict_gen(training_set, batch_size=64)
```

We are all set! Let's fit our `TfidfVectorizer` using the `tokenized_set`, and disabling the embedded tokenizer.

```python
from sklearn.feature_extraction.text import TfidfVectorizer

vectorizer = TfidfVectorizer(
    tokenizer=lambda x: x, lowercase=False, max_df=0.95, min_df=0.01
).fit(tokenized_set)
```

We now need to save the vocabulary we just fitted to disk, before writing our on vectorizer `Model`.

Of course, one could serialize the `TfidfVectorizer`, but there are many reasons why we would not want this in production code:

- `TfidfVectorizer` is only used to build the vocabulary using neat features such as min/max document frequencies, which are no longer useful during inference
- it requires a heavy code dependency: `scikit-learn`, only for vectorization
- pickling scikit-learn models come with some tricky issues relative to dependency, version and security

It is also common practice to separate the research / training phase, from the production phase.

As a result, we will be implementing our own vectorizer for production using `modelkit`, based on the vocabulary created with scikit-learn's `TfidfVectorizer`.

We just need to write a list of strings to disk:

```python
# we only keep strings from the vocabulary
# we will be using our own str -> int mapping
vocabulary = next(zip(*sorted(vectorizer.vocabulary_.items(), key=lambda x: x[1])))
with open("vocabulary.txt", "w", encoding="utf-8") as f:
    for row in vocabulary:
        f.write(row + "\n")
```

### Using the file in a Model

In this subsection, you will learn how to leverage the basics of Modelkit's Assets management.

!!! note
    Most of the features (assets remote storage, updates, versioning, etc.) will not be adressed in this tutorial, *but are the way to go when things get serious.*

First, let's implement our `Vectorizer` as a `modelkit.Model` which loads the `vocabulary.txt` file we just created:

```python hl_lines="7 10"
import modelkit

from typing import List


class Vectorizer(modelkit.Model):
    CONFIGURATIONS = {"imdb_vectorizer": {"asset": "vocabulary.txt"}}

    def _load(self):
        self.vocabulary = {}
        with open(self.asset_path, "r", encoding="utf-8") as f:
            for i, k in enumerate(f):
                self.vocabulary[k.strip()] = i

```

Here, we define a `CONFIGURATIONS` class attribute, which lets `modelkit` know how to find the vocabulary. `vocabulary.txt` will be found in the current working directory, and its absolute path written to the `Vectorizer.asset_path` attribute before `_load` is called.

??? note "Remote assets"
    When assets are stored remotely, the remote versioned asset is retrieved and cached on the local disk *before* the `_load` method is called, and its local path is set in the `self.asset_path` attribute.

    `modelkit` *guarantees* that whenever `_load` is called, the file is present and its absolute path is written to `Model.asset_path`.


??? note "What can be an asset"
    An asset can be anything (a file, a directory), and the user is responsible for defining the loading logic in `_load`. 
    You can refer to it with a relative path (which will be relative to the current working directeory), an absolute path, or a remote asset specification.

In this case, it is rather straighforward: `self.asset_path` directly points to `vocabulary.txt`.


In addition, the `imdb_vectorizer` _configuration key_ can now be used to refer to the `Vectorizer` in a `ModelLibrary` object. This allows you to define multiple `Vectorizer` objects with different vocabularies, without rewriting the prediction logic.

## Prediction

Now let us add a more complex prediction logic and input specification:

```python hl_lines="15 17"
import numpy as np
import modelkit

from typing import List


class Vectorizer(modelkit.Model[List[str], List[int]]):
    CONFIGURATIONS = {"imdb_vectorizer": {"asset": "vocabulary.txt"}}

    def _load(self):
        self.vocabulary = {}
        with open(self.asset_path, "r", encoding="utf-8") as f:
            for i, k in enumerate(f):
                self.vocabulary[k.strip()] = i + 2
        self._vectorizer = np.vectorize(lambda x: self.vocabulary.get(x, 1))

    def _predict(self, tokens, length=None, drop_oov=True):
        vectorized = (
            np.array(self._vectorizer(tokens), dtype=np.int)
            if tokens
            else np.array([], dtype=int)
        )
        if drop_oov and len(vectorized):
            vectorized = np.delete(vectorized, vectorized == 1)
        if not length:
            return vectorized.tolist()
        result = np.zeros(length)
        vectorized = vectorized[:length]
        result[: len(vectorized)] = vectorized
        return result.tolist()
```

We add several advanced features, first, to deal with out of vocabulary or padding tokens, we reserve the following integers:

- `0` for padding
- `1` for the unknown token (out-of-vocabulary words)
- `2+i` for known vocabulary words


We use `np.vectorize` to map a tokens list to an indices list, which we store in the `_vectorize` attribute in the `_load`.


We also add keyword arguments to the `_predict`:  `length` and `drop_oov`. These can be used during prediction as well, and would be passed to `_predict` or `_predict_batch`:

```python
vectorizer = modelkit.load_model("imdb_vectorizer", models=Vectorizer)
vectorizer.predict(item, length=10, drop_oov=False)
vectorizer.predict_batch(items, length=10, drop_oov=False)
vectorizer.predict_gen(items, length=10, drop_oov=False)
```


### Test cases 

Now let us add test cases too. The only trick here is that we have to add the information about our new keyword arguments when we want to test different values.

To do so, we use the `keyword_args` field in the test cases:

```python hl_lines="7 12 18 23 28"
class Vectorizer(modelkit.Model[List[str], List[int]]):
    ...

    TEST_CASES = [
        {"item": [], "result": []},
        {"item": [], "keyword_args": {"length": 10}, "result": [0] * 10},
        {"item": ["movie"], "result": [888]},
        {"item": ["unknown_token"], "result": []},
        {
            "item": ["unknown_token"],
            "keyword_args": {"drop_oov": False},
            "result": [1],
        },
        {"item": ["movie", "unknown_token", "scenes"], "result": [888, 1156]},
        {
            "item": ["movie", "unknown_token", "scenes"],
            "keyword_args": {"drop_oov": False},
            "result": [888, 1, 1156],
        },
        {
            "item": ["movie", "unknown_token", "scenes"],
            "keyword_args": {"length": 10},
            "result": [888, 1156, 0, 0, 0, 0, 0, 0, 0, 0],
        },
        {
            "item": ["movie", "unknown_token", "scenes"],
            "keyword_args": {"length": 10, "drop_oov": False},
            "result": [888, 1, 1156, 0, 0, 0, 0, 0, 0, 0],
        },
    ]
    ...
``` 

### Final vectorizer

Putting it all together, we obtain:

```python 
import modelkit
import numpy as np

from typing import List


class Vectorizer(modelkit.Model[List[str], List[int]]):
    CONFIGURATIONS = {"imdb_vectorizer": {"asset": "vocabulary.txt"}}
    TEST_CASES = [
        {"item": [], "result": []},
        {"item": [], "keyword_args": {"length": 10}, "result": [0] * 10},
        {"item": ["movie"], "result": [888]},
        {"item": ["unknown_token"], "result": []},
        {
            "item": ["unknown_token"],
            "keyword_args": {"drop_oov": False},
            "result": [1],
        },
        {"item": ["movie", "unknown_token", "scenes"], "result": [888, 1156]},
        {
            "item": ["movie", "unknown_token", "scenes"],
            "keyword_args": {"drop_oov": False},
            "result": [888, 1, 1156],
        },
        {
            "item": ["movie", "unknown_token", "scenes"],
            "keyword_args": {"length": 10},
            "result": [888, 1156, 0, 0, 0, 0, 0, 0, 0, 0],
        },
        {
            "item": ["movie", "unknown_token", "scenes"],
            "keyword_args": {"length": 10, "drop_oov": False},
            "result": [888, 1, 1156, 0, 0, 0, 0, 0, 0, 0],
        },
    ]

    def _load(self):
        self.vocabulary = {}
        with open(self.asset_path, "r", encoding="utf-8") as f:
            for i, k in enumerate(f):
                self.vocabulary[k.strip()] = i + 2
        self._vectorizer = np.vectorize(lambda x: self.vocabulary.get(x, 1))

    def _predict(self, tokens, length=None, drop_oov=True):
        vectorized = (
            np.array(self._vectorizer(tokens), dtype=np.int)
            if tokens
            else np.array([], dtype=int)
        )
        if drop_oov and len(vectorized):
            vectorized = np.delete(vectorized, vectorized == 1)
        if not length:
            return vectorized.tolist()
        result = np.zeros(length)
        vectorized = vectorized[:length]
        result[: len(vectorized)] = vectorized
        return result.tolist()
```

In the next section, we will train a classifier using the Tokenizer and Vectorizer models we just created. This will show us how to compose and store models in `modelkit`.
