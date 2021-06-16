In this section, we will cover the basics of Modelkit's API, and use Spacy as tokenizer for our NLP pipeline.

### Initialization
Once you have set up a fresh python environment, let's install modelkit, spacy and grab the small english model.

```
pip install modelkit spacy
python -m spacy download en_core_web_sm
```

### Basics

To define a Modelkit Model, you need to:

- create class inheriting from `modelkit.Model` 
- implement a `_predict` method

To begin with, let's create a minimal tokenizer in the most concise way:

```python
import modelkit


class Tokenizer(modelkit.Model):
    def _predict(self, text):
        return text.split()
```

That's it ! As you can see, it is _very_ minimal, and probably not sufficient for a lot of usages.

It is just the necessary to define a Modelkit Model.

You are now able to instantiate and call it using the following methods:
```python
tokenizer = Tokenizer()

# for single predictions
tokenizer("I am a Data Scientist from Amiens, France")
tokenizer.predict("I am a Data Scientist from Amiens, France")

# for batch predictions
tokenizer.predict_batch(["I am a Data Scientist from Amiens, France"])

# for generators
tokenizer.predict_gen(("I am a Data Scientist from Amiens, France",))

```

### Leveraging spacy

For now, the tokenizer pipeline is too simple to show-off.

Let's make use of Spacy and complexify things a little, so that to have a prod-like tokenizer. (fortunately, we will not be digging into weird customer rules)

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
            for t in self.nlp(text)
            if t.is_ascii and len(t) > 1 and not (t.is_punct or t.is_stop or t.is_digit)
        ]
```

Spacy pipelines come with several different cool features.

Since we will only be using the tokenizer, let's not forget to disable the ones we will not be needing.

As you can see, the `_load` method was implemented: it is where all the assets, artefacts, models etc. are loaded once the model is instantiated.

This way, your model will benefit from further features that will be covered in the next sections such as *lazy_loading* and *dependency management*.

This is why we store the spacy pipeline in the `_load` method, not in the `_predict` nor the `__init__` methods.

```python
tokenizer = Tokenizer()
tokenizer.predict("Spacy is a great lib for NLP 😀")
# ['spacy', 'great', 'lib', 'nlp']

```

### Batch computing

So far, we have only implemented the `_predict` method so that to tokenize one sentence at a time.

While this is relevant for many usages, when calls are rather simple and straightforward (such as the `text.split()` tokenizer),
it's a whole other thing when you deal with more complex functions leveraging heavy weapons (Spacy, Tensorflow, PyTorch etc.) or distant calls (TF Serving, database accesses etc.) 

To do so, Modelkit allows you to define a `_predict_batch` method to _kill N birds with one stone_.

The following section shows how to properly use Spacy's `pipe` method to tokenize items by batch.

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

This way, we reduce by two the time needed to tokenize batches of data, compared to a simple `_predict` call.

Benchmark example using ipython:
```
%timeit [Tokenizer().predict("Spacy is a great lib for NLP") for _ in range(100)]
# 11.1 ms ± 203 µs per loop on a 2020 Macbook Pro.

%timeit Tokenizer().predict_batch(["Spacy is a great lib for NLP] * 100, batch_size=64)
# 5.5 ms ± 105 µs per loop on a 2020 Macbook Pro.
```

### Testing

So far, more or less complex rules have been designed.

Modelkit allows you to add tests right next to your class definition to serve as documentation, in addition to ensuring everything behaves as intended.

```python
import modelkit
import spacy


class Tokenizer(modelkit.Model):
    TEST_CASES = {
        "cases": [
            {"item": "", "result": []},
            {"item": "NLP 101", "result": ["nlp"]},
            {
                "item": "I'm loving the Spacy 101 course !!!ù*`^@😀",
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

These tests can be executed in two ways.

Manually, in an interative programming tool such as ipython, jupyter etc. using the `test` method:
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

Or with pytest via [the Modelkit autotesting fixture](../library/testing.html#modellibrary-fixture-and-autotesting)

Woops, seems like we need to fix the last test!

### Typing

When it comes to production, it is good practice to type models' inputs and outputs to ensure consistency and validation between calls, dependencies and services.

It also allows you to better/faster understand how to use a given model, in addition to benefit from static type checkers such as mypy.

Modelkit manages typing in the following way: `Model[input_type, output_type]`

It also support the power of Pydantic, as we will see in the next section.

Let's type our previous Tokenizer and conclude this first part:

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
                "item": "I'm loving the Spacy 101 course !!!ù*`^@😀",
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

This way, the following will raise a Modelkit `ItemValidationException`:

```python
Tokenizer().predict(["list", "of", "tokens", "will", "raise", "an", "exception"])
```

That's it! To sum up this first Modelkit overview, you have learned:

- How to create a basic Model class by inheriting from `modelkit.Model` and implementing a `_predict` method
- How to correctly load artefacts/assets by overloading the `_load` method
- How to leverage batch computing to speed up execution by implementing a `_predict_batch` method
- How to add tests to ensure everything works as intended using `TEST_CASES` right in your model definition
- How to add typing to ensure consistency and validation: `modelkit.Model[input_type, output_type]`

### Final tokenizer

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
                "item": "I'm loving the Spacy 101 course !!!ù*`^@😀",
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

