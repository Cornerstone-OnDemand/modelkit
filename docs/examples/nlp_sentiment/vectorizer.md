In this section, we will fit and implement a custom text vectorizer based on the sentiment analysis IMDB dataset.

It will be the opportunity to go through Modelkit's Assets Management basics, to learn how to fetch artefacts, in addition to getting even more familiar with its API.

### Initialization

To begin with, let's download the IMDB reviews dataset:

```
# download the remote archive
curl https://ai.stanford.edu/~amaas/data/sentiment/aclImdb_v1.tar.gz --output imdb.tar.gz
# untar it
tar -xvf imdb.tar.gz
# remove the unsupervised directory we will not be using
rm -rf aclImdb/train/unsup
```

This dataset is organized in train/test directories, containing pos (positive) / neg (negative) subfolders corresponding to the target classes to predict.

The different files only consist in longer or shorter text reviews left by IMDB users, one file corresponding to one review.

### Fitting

First thing first, let's define a helper function to read through the training set.

We will only be using generators to avoid loading up the entire dataset in memory, and take advantage of the `predict_gen` method of Modelkit models.

```python 
import glob
from typing import Generator

def read_dataset(path: str) -> Generator[str, None, None]:
    for review in glob.glob(os.path.join(path, "*.txt")):
        with open(review, 'r', encoding='utf-8') as f:
            yield f.read()
```

Before fitting our Scikit-Learn `TfidfVectorizer`, we need to tokenize our dataset first.

While this vectorizer includes a tokenizer, we will be using the one implemented in the first section.

```python
import itertools
import os

training_set = itertools.chain(
    read_dataset(os.path.join("aclImdb", "train", "pos")),
    read_dataset(os.path.join("aclImdb", "train", "neg")),
)
tokenized_set = Tokenizer().predict_gen(training_set)
```

By using the `predict_gen` method, we are able to read huge texts corpora without having Out-Of-Memory issues.

Each review will be tokenized one by one. As you may remember, you can also speed up execution by setting a `batch_size` greater than one to process these reviews batch by batch.

```python
# here, an example with a 64 batch size
tokenized_set = Tokenizer().predict_gen(training_set, batch_size=64)
```

We are all set! Let's fit our `TfidfVectorizer` using the tokenized_set, and disabling the embedded tokenizer.

```python
from sklearn.feature_extraction.text import TfidfVectorizer

vectorizer = TfidfVectorizer(
    tokenizer=lambda x: x, lowercase=False, max_df=0.95, min_df=0.01
).fit(tokenized_set)
```

Then, we will just keep the just-fitted vocabulary and dump it to disk, before writing our on vectorizer.

Of course, one could stick with the TfidfVectorizer, however the idea here is not to rely on it for production for the following reasons:

- its goal here is just to help build the vocabulary using neat features such as min/max document frequencies
- it would require a heavy dependency: scikit-learn, just for vectorization
- pickling scikit-learn models come with some tricky issues relative to dependency, version and security management that we will not be digging here

It is also common practice to separate the research / training phase, from the production phase.

As such, we will be implementing our own vectorizer for production using Modelkit, based on the work of scikit-learn's `TfidfVectorizer`.

All in all, we just need to dump a list of strings to disk.

```python
# we only keep strings from the vocabulary
# we will be using our own str -> int mapping
vocabulary = next(zip(*sorted(vectorizer.vocabulary_.items(), key=lambda x: x[1])))
with open("vocabulary.txt", "w", encoding="utf-8") as f:
    for row in vocabulary:
        f.write(row + "\n")
```

### Asset retrieval

In this subsection, you will learn how to leverage the basics of Modelkit's Assets Management system.

Keep in mind that most of its powerful features (assets pushing, updating, versioning, retrieval) will not be adressed in this tutorial, *but are the way to go when things get serious.*

First, let's implement our Vectorizer as a Modelkit Model, the same way we did for the Tokenizer:

- inheriting from Model, implementing the `_predict` method
- typing ins and outs
- testing its behavior
- dealing with fixed sizes and out-of-vocabulary tokens

```python
import numpy as np
import modelkit

from typing import List


class Vectorizer(modelkit.Model[List[str], List[int]]):
    TEST_CASES = {
        "cases": [
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
    }


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

As you can see here, there are some missing pieces in the puzzle.

However, you probably noticed one new piece in TEST_CASES: `keyword_args`.

This allows you to pass extra parameters to your `_predict`, in this case: `length`, `drop_oov`

Let's figure out what the other pieces are.

To begin with, you need to be introduced to the `CONFIGURATIONS` map:

```python
class Vectorizer(modelkit.Model[List[str], List[int]]):
    CONFIGURATIONS = {
        "imdb_vectorizer": {
            "asset": "vocabulary.txt"
        }
    }
    ...
```

The `CONFIGURATIONS` map is the cornerstone of the Assets Management system.
It is the best way to:

- name models
- use local/remote/versioned assets
- make models depend on other models
- use different assets, with the same implementation
- get models, by their name using Modelkit's `ModelLibrary`

In the previous code example, you can see that we named our vectorizer `imdb_vectorizer`, it relies on a local asset whose direct path is `vocabulary.txt`.

What about the `_load` method ? Let's implement it: 

```python
import numpy as np


class Vectorizer(modelkit.Model[List[str], List[int]]):
    CONFIGURATIONS = {"imdb_vectorizer": {"asset": "vocabulary.txt"}}
    ...
    def _load(self):
        self.vocabulary = {}
        with open(self.asset_path, "r", encoding="utf-8") as f:
            for i, k in enumerate(f):
                self.vocabulary[k.strip()] = i + 2
        self._vectorizer = np.vectorize(lambda x: self.vocabulary.get(x, 1))

```

Right before the `_load` method is called, the local/remote/versioned asset is retrieved and cached on the caller's disk, and its local path is set in the `self.asset_path` attribute.

In this case, it is rather straighforward: `self.asset_path` directly points to `vocabulary.txt`.

Hence, we just need to iterate through it, populate our vocabulary dictionary and map those tokens to their number of line + 2:

- 0 for padding
- 1 for the unknown token (out-of-vocabulary words)
- 2 for everything else

Finally, the `np.vectorize` will help map a tokens list to an indices list.

### Final vectorizer

Here is the entire `Vectorizer` puzzle:

```python 
import modelkit
import numpy as np

from typing import List


class Vectorizer(modelkit.Model[List[str], List[int]]):
    CONFIGURATIONS = {"imdb_vectorizer": {"asset": "vocabulary.txt"}}
    TEST_CASES = {
        "cases": [
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
    }

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

