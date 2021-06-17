In this section, we will cover the basics of `modelkit`'s API, and use spaCy as tokenizer for our NLP pipeline.

## Installation 
Once you have set up a fresh python environment, let's install `modelkit`, `spacy` and grab the small english model.

```
pip install modelkit spacy
python -m spacy download en_core_web_sm
```

## Simple Model predict

To define a modelkit `Model`, you need to:

- create class inheriting from `modelkit.Model` 
- implement a `_predict` method

To begin with, let's create a minimal tokenizer:

```python
import modelkit


class Tokenizer(modelkit.Model):
    def _predict(self, text):
        return text.split()
```

That's it! It is _very_ minimal, but sufficient to define a modelkit `Model`.

You can now instantiate and call the `Model`:

```python
tokenizer = Tokenizer()

tokenizer.predict("I am a Data Scientist from Amiens, France")
```

??? note "Other ways to call predict"
    It is also possible to get predictions for batches (lists of items):

    ```python
    tokenizer.predict_batch([
        "I am a Data Scientist from Amiens, France", 
        "And I use modelkit"
    ])
    ```

    or call predict as a generator:

    ```python
    for prediction in tokenizer.predict_gen(("I am a Data Scientist from Amiens, France",)):
        print(prediction)
    ```

### Complex `Model` initialization

Let's now use [spaCy](https://spacy.io/) to get closer to a production-ready tokenizer.

This will also help demonstrate additional Modelkit features.

```python
import modelkit
import spacy

class Tokenizer(modelkit.Model):
    def _load(self):
        self.nlp = spacy.load(
            "en_core_web_sm",
            disable=[
                "parser",
                "ner",
                "tagger",
                "lemmatizer",
                "tok2vec",
                "attribute_ruler",
            ],
        )

    def _predict(self, text):
        text = " ".join(text.replace("<br", "").replace("/>", "").split())
        return [
            t.lower_
            for t in self.nlp(text)  # self.nlp is guaranteed to be initialized
            if t.is_ascii and len(t) > 1 and not (t.is_punct or t.is_stop or t.is_digit)
        ]
```

We implement a `_load` method, which is where any asset, artifact, and other complex model attributes are created. 

This method will be called exactly once in the lifetime of the `Model` object. 

We define the spacy pipeline in the `_load` method (as opposed to `_predict` or the `__init__` methods), because it allows your model to benefit from advanced `modelkit` features such as *lazy loading* and *dependency management*.

Since we will only be using the tokenizer and not the many other cool spacy features, let's not forget to disable them.

We can instantiate the model and get predictions as before:
```python
tokenizer = Tokenizer() # _load is called
tokenizer.predict("spaCy is a great lib for NLP 😀")
# ['spacy', 'great', 'lib', 'nlp']
```

### Batch computation

So far, we have only implemented the `_predict` method, which tokenizes items one by one. 

In many instances, however, models will be called with many items at once, and we can leverage vectorization for speedups. This is particularly true when using other frameworks (Numpy, spaCy, Tensorflow, PyTorch etc.), or distant calls (TF Serving, database accesses etc.).

To leverage batching, modelkit allows you to define a `_predict_batch` method to process lists of items, and thus _kill multiple birds with one stone_.

Here we use spaCy's `pipe` method to tokenize items in batch:

```python
import modelkit
import spacy


class Tokenizer(modelkit.Model):
    def _load(self):
        self.nlp = spacy.load(
            "en_core_web_sm",
            disable=[
                "parser",
                "ner",
                "tagger",
                "lemmatizer",
                "tok2vec",
                "attribute_ruler",
            ],
        )

    def _predict_batch(self, texts):
        texts = [
            " ".join(text.replace("<br", "").replace("/>", "").split())
            for text in texts
        ]
        return [
            [
                t.lower_
                for t in text
                if t.is_ascii
                and len(t) > 1
                and not (t.is_punct or t.is_stop or t.is_digit)
            ]
            for text in self.nlp.pipe(texts, batch_size=len(texts))
        ]
```

Compared to the implementation with a `_predict` call, the time needed to tokenize batches of data is divided by 2.

For example, using ipython's `timeit` to process a list of a 100 strings:
```
%timeit [Tokenizer().predict("spaCy is a great lib for NLP") for _ in range(100)]
# 11.1 ms ± 203 µs per loop on a 2020 Macbook Pro.

%timeit Tokenizer().predict_batch(["spaCy is a great lib for NLP] * 100, batch_size=64)
# 5.5 ms ± 105 µs per loop on a 2020 Macbook Pro.
```

??? note "Caching predictions"
    `modelkit` also allows you to use prediction caching (using Redis, or Python native caches) to improve computation times when the same items are seen over and over


## Additional features

### Tests

So far the tokenizer is relatively simple, but it is always useful to test your code.

`modelkit` encourages you to add test cases alongside the `Model` class definition to ensure that it behaves as intended, and serve as documentation.

```python
import modelkit
import spacy


class Tokenizer(modelkit.Model):
    TEST_CASES = {
        "cases": [
            {"item": "", "result": []},
            {"item": "NLP 101", "result": ["nlp"]},
            {
                "item": "I'm loving the spaCy 101 course !!!ù*`^@😀",
                "result": ["loving", "spacy", "course"],
            },
            {
                "item": "<br/>prepare things for IMDB<br/>",
                "result": ["prepare", "things", "imdb"],
            },
            {
                "item": "<br/>a b c data<br/>      e scientist",
                "result": ["data", "scientist", "failing", "test"],
            },  # fails as intended
        ]
    }

    def _load(self):
        self.nlp = spacy.load(
            "en_core_web_sm",
            disable=[
                "parser",
                "ner",
                "tagger",
                "lemmatizer",
                "tok2vec",
                "attribute_ruler",
            ],
        )

    def _predict_batch(self, texts):
        texts = [
            " ".join(text.replace("<br", "").replace("/>", "").split())
            for text in texts
        ]
        return [
            [
                t.lower_
                for t in text
                if t.is_ascii
                and len(t) > 1
                and not (t.is_punct or t.is_stop or t.is_digit)
            ]
            for text in self.nlp.pipe(texts, batch_size=len(texts))
        ]
```

You can run these test cases in the interactive programming tool of your choice (e.g. `ipython`, `jupyter` etc.) using the `test` method:

```python
Tokenizer().test()
# TEST 1: SUCCESS
# TEST 2: SUCCESS
# TEST 3: SUCCESS
# TEST 4: SUCCESS
# TEST 5: FAILED test failed on item
# item = '<br/>a b c data<br/>      e scientist'                                               
# expected = list instance                                                                     
# result = list instance                                                                       
```

??? note "Run using pytest"
    It is also possible to automatically test all models using the `pytest` integration, using [the Modelkit autotesting fixture](../library/testing.md#modellibrary-fixture-and-autotesting).

Woops, seems like we need to fix the last test!

### Input and output specification

It is good practice to specify inputs and outputs of models in production code

This allows calls to be validated, thus ensuring consistency between calls, dependencies, services, and raising alerts when Models are not called as expected.

This is also good for documentation, to understand how to use a given model, and during development to benefit from static type checking (e.g. with [mypy](https://github.com/python/mypy)).

`modelkit` allows you to define the expected input and output types of your model by subclassing `Model[input_type, output_type]`, where `input_type` and `output_type` can be standard Python types, dataclasses, or complex [pydantic](https://pydantic-docs.helpmanual.io/) models.

Let's add specification our Tokenizer to conclude this first part:

```python
from typing import List

import modelkit
import spacy


class Tokenizer(modelkit.Model[str, List[str]]):
    TEST_CASES = {
        "cases": [
            {"item": "", "result": []},
            {"item": "NLP 101", "result": ["nlp"]},
            {
                "item": "I'm loving the spaCy 101 course !!!ù*`^@😀",
                "result": ["loving", "spacy", "course"],
            },
            {
                "item": "<br/>prepare things for IMDB<br/>",
                "result": ["prepare", "things", "imdb"],
            },
            {
                "item": "<br/>a b c data<br/>      e scientist",
                "result": ["data", "scientist", "failing", "test"],
            },  # fails as intended
        ]
    }

    def _load(self):
        self.nlp = spacy.load(
            "en_core_web_sm",
            disable=[
                "parser",
                "ner",
                "tagger",
                "lemmatizer",
                "tok2vec",
                "attribute_ruler",
            ],
        )

    def _predict_batch(self, texts):
        texts = [
            " ".join(text.replace("<br", "").replace("/>", "").split())
            for text in texts
        ]
        return [
            [
                t.lower_
                for t in text
                if t.is_ascii
                and len(t) > 1
                and not (t.is_punct or t.is_stop or t.is_digit)
            ]
            for text in self.nlp.pipe(texts, batch_size=len(texts))
        ]
```

Calling the model with an unexpected type will raise a Modelkit `ItemValidationException`:

```python
Tokenizer().predict([1, 2, 3, 4])
```

And `mypy` will raise errors if it encounters calls that are not correct:
```python
result : int = Tokenizer().predict("some text")
```

## Conclusion

That's it! 

In this `modelkit` introduction, you have learned:

- How to create a basic `Model` by inheriting from `modelkit.Model` and implementing a `_predict` method
- How to correctly *load* artefacts/assets by overriding the `_load` method
- How to leverage *batch computing* to speed up execution by implementing a `_predict_batch` method
- How to *add tests* to ensure everything works as intended using `TEST_CASES` right in your model definition
- How to add specification to your model's inputs and outputs using `modelkit.Model[input_type, output_type]`

### Final Tokenizer code

```python
from typing import List

import modelkit
import spacy


class Tokenizer(modelkit.Model[str, List[str]]):
    CONFIGURATIONS = {"imdb_tokenizer": {}}
    TEST_CASES = {
        "cases": [
            {"item": "", "result": []},
            {"item": "NLP 101", "result": ["nlp"]},
            {
                "item": "I'm loving the spaCy 101 course !!!ù*`^@😀",
                "result": ["loving", "spacy", "course"],
            },
            {
                "item": "<br/>prepare things for IMDB<br/>",
                "result": ["prepare", "things", "imdb"],
            },
            {
                "item": "<br/>a b c data<br/>      e scientist",
                "result": ["data", "scientist"],
            },
        ]
    }

    def _load(self):
        self.nlp = spacy.load(
            "en_core_web_sm",
            disable=[
                "parser",
                "ner",
                "tagger",
                "lemmatizer",
                "tok2vec",
                "attribute_ruler",
            ],
        )

    def _predict_batch(self, texts):
        texts = [
            " ".join(text.replace("<br", "").replace("/>", "").split())
            for text in texts
        ]
        return [
            [
                t.lower_
                for t in text
                if t.is_ascii
                and len(t) > 1
                and not (t.is_punct or t.is_stop or t.is_digit)
            ]
            for text in self.nlp.pipe(texts, batch_size=len(texts))
        ]

```

As you may have seen, there is a `CONFIGURATIONS` map in the class definition, we will cover it in the next section.

