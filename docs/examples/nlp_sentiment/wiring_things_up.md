You have now seen most dev features, implementing them from the Tokenizer to the Classifier.

While it works from end-to-end, the API is still not really user-friendly and asks to wire things up as we did in the last section.

Moreover, the classifier still seems kind of basic, and does not implement many features that make Modelkit relevant.

Let's see how we can enhance it, and take the opportuniy to review all Modelkit's features we have seen so far, and discover new features too.

### Dependency management

Modelkit's Asset Management system allows you to add other models as dependencies.

For our use-case, it might be relevant for the classifier to take raw string reviews as input, and output a class label ("good" or "bad").

This could be done using the `model_dependencies` key in the `CONFIGURATIONS` map, and by adding the `Tokenizer` and the `Vectorizer` as dependencies.

Modelkit takes care of loading up the dependencies right before your model's instantiation.
As such, loaded dependencies are discoverable from `self.model_dependencies` anytime after the `_load` method is called.

```python
import numpy as np
import modelkit
import tensorflow as tf


class Classifier(modelkit.Model[str, str]):
    CONFIGURATIONS = {
        "imdb_classifier": {
            "asset": "imdb_model.h5",
            "model_dependencies": {"imdb_tokenizer", "imdb_vectorizer"}
        },
    }
    def _load(self):
        self.model = tf.keras.models.load_model(self.asset_path)
        self.tokenizer = self.model_dependencies["imdb_tokenizer"]
        self.vectorizer = self.model_dependencies["imdb_vectorizer"]
        self.prediction_mapper = np.vectorize(lambda x: "good" if x >= 0.5 else "bad")

    def _predict_batch(self, reviews):
        # this looks like the previous end-to-end example from the previous section
        cleaned_reviews = self.tokenizer.predict_batch(reviews)
        vectorized_reviews = self.vectorizer.predict_batch(cleaned_reviews, length=64)
        predictions_scores = self.model.predict(vectorized_reviews)
        predictions_classes = self.prediction_mapper(predictions_scores).reshape(-1)
        return predictions_classes


model_library = modelkit.ModelLibrary(models=[Tokenizer, Vectorizer, Classifier])
classifier = model_library.get("imdb_classifier")
classifier.predict("This movie is freaking awesome, I love the main character")
# good
classifier.predict("this movie sucks, it's the worst I have ever seen")
# bad
```
This definitely looks easier to use, and the classifier now seems more relevant.

### Tests, again

We might want to add the score, in addition to some tests as well:

```python
import numpy as np
import modelkit
import tensorflow as tf

from typing import Dict, Union

class Classifier(modelkit.Model[str, Dict[str, Union[str, float]]]):
    CONFIGURATIONS = {
        "imdb_classifier": {
            "asset": "imdb_model.h5",
            "model_dependencies": {"imdb_tokenizer", "imdb_vectorizer"},
        },
    }
    TEST_CASES = {
        "cases": [
            {
                "item": "i love this film, it's the best i've ever seen",
                "result": {"score": 0.8441019058227539, "label": "good"},
            },
            {
                "item": "this movie sucks, it's the worst I have ever seen",
                "result": {"score": 0.1625385582447052, "label": "bad"},
            },
        ]
    }

    def _load(self):
        self.model = tf.keras.models.load_model(self.asset_path)
        self.tokenizer = self.model_dependencies["imdb_tokenizer"]
        self.vectorizer = self.model_dependencies["imdb_vectorizer"]
        self.prediction_mapper = np.vectorize(lambda x: "good" if x >= 0.5 else "bad")

    def _predict_batch(self, reviews):
        cleaned_reviews = self.tokenizer.predict_batch(reviews)
        vectorized_reviews = self.vectorizer.predict_batch(cleaned_reviews, length=64)
        predictions_scores = self.model.predict(vectorized_reviews)
        predictions_classes = self.prediction_mapper(predictions_scores).reshape(-1)
        predictions = [
            {"score": score, "label": label}
            for score, label in zip(predictions_scores, predictions_classes)
        ]
        return predictions


model_library = modelkit.ModelLibrary(models=[Tokenizer, Vectorizer, Classifier])
classifier = model_library.get("imdb_classifier")
classifier.test()
```

### Pydantic

We now output a score and its corresponding label in a `Dict`.

For production usages, Modelkit can leverage the power of Pydantic to validate both input and output items, instead of the standard python way.

It is even more relevant, readable and understandable as your number of input / output features grow (such as a `rating` field in the next example)

The only usage difference: inputs and outputs are now python objects and need to be managed as such.


```python

from typing import Optional

import modelkit
import numpy as np
import pydantic
import tensorflow as tf


class MovieReviewItem(pydantic.BaseModel):
    text: str
    rating: Optional[float] = None  # could be useful in the future ? but not mandatory

class MovieSentimentItem(pydantic.BaseModel):
    label: str
    score: float

class Classifier(modelkit.Model[MovieReviewItem, MovieSentimentItem]):
    CONFIGURATIONS = {
        "imdb_classifier": {
            "asset": "imdb_model.h5",
            "model_dependencies": {"imdb_tokenizer", "imdb_vectorizer"},
        },
    }
    TEST_CASES = {
        "cases": [
            {
                "item": {"text": "i love this film, it's the best I've ever seen"},
                "result": {"score": 0.8441019058227539, "label": "good"},
            },
            {
                "item": {"text": "this movie sucks, it's the worst I have ever seen"},
                "result": {"score": 0.1625385582447052, "label": "bad"},
            },
        ]
    }

    def _load(self):
        self.model = tf.keras.models.load_model(self.asset_path)
        self.tokenizer = self.model_dependencies["imdb_tokenizer"]
        self.vectorizer = self.model_dependencies["imdb_vectorizer"]
        self.prediction_mapper = np.vectorize(lambda x: "good" if x >= 0.5 else "bad")

    def _predict_batch(self, reviews):
        texts = (review.text for review in reviews)
        cleaned_reviews = self.tokenizer.predict_batch(texts)
        vectorized_reviews = self.vectorizer.predict_batch(cleaned_reviews, length=64)
        predictions_scores = self.model.predict(vectorized_reviews)
        predictions_classes = self.prediction_mapper(predictions_scores).reshape(-1)
        predictions = [
            {"score": score, "label": label}
            for score, label in zip(predictions_scores, predictions_classes)
        ]
        return predictions

model_library = modelkit.ModelLibrary(models=[Tokenizer, Vectorizer, Classifier])
classifier = model_library.get("imdb_classifier")
classifier.test()
prediction = classifier.predict({"text": "I love the main character"})
print(prediction)
# MovieSentimentItem(label='good', score=0.6801363825798035)
print(prediction.label) 
# good
print(prediction.score) 
# 0.6801363825798035
```

You can also rename your model dependencies from within the `CONFIGURATIONS` map, 
so that to make some tricky dependencies names more understandable, of if you do not know their exact name in advance:

```python
import modelkit

class Classifier(modelkit.Model[MovieReviewItem, MovieSentimentItem]):
    CONFIGURATIONS = {
        "imdb_classifier": {
            "asset": "imdb_model.h5",
            "model_dependencies": {
                "tokenizer": "imdb_tokenizer",
                "vectorizer": "imdb_vectorizer",
            },  # renaming dependencies here
        },
    }
    def _load(self):
        self.tokenizer = self.model_dependencies[
            "tokenizer"
        ]
        self.vectorizer = self.model_dependencies[
            "vectorizer"
        ]
    ...

```

### Multiple configurations

To conclude this tutorial, let's briefly see how to define multiple configurations, and why.

What if this model went to production, most clients are happy with it, but some are not. 
You start from scratch: redefining your tokenizer, then your vectorizer, 
then re-ran your classifier's training loop with a different architecture and more data, and saved it preciously.
Since you have always been the original guy in the room, all the new models now have a "_SOTA" suffix.

You managed to keep the same inputs, outputs, pipeline architecture and made your process reproductible.

"That should do it !", you are yelling across the open space.

However, you probably do not want to surprise your clients with a new model without informing them before.

Some might want to stick with the old one, while the unhappy ones would want to change ASAP.

Modelkit has got your back, and allows you to define multiple configurations while keeping the exact same code.

Here is how you would process:

```python
import modelkit

class Classifier(modelkit.Model[MovieReviewItem, MovieSentimentItem]):
    CONFIGURATIONS = {
        "classifier": {
            "asset": "imdb_model.h5",
            "model_dependencies": {
                "tokenizer": "imdb_tokenizer",
                "vectorizer": "imdb_vectorizer",
            },
            "test_cases": [
                {
                    "item": {"text": "i love this film, it's the best i've ever seen"},
                    "result": {"score": 0.8441019058227539, "label": "good"},
                },
                {
                    "item": {
                        "text": "this movie sucks, it's the worst I have ever seen"
                    },
                    "result": {"score": 0.1625385582447052, "label": "bad"},
                },
            ],
        },
        "classifier_SOTA": {
            "asset": "imdb_model_SOTA.h5",
            "model_dependencies": {
                "tokenizer": "imdb_tokenizer_SOTA",
                "vectorizer": "imdb_vectorizer_SOTA",
            },
            "test_cases": [
                {
                    "item": {"text": "i love this film, it's the best i've ever seen"},
                    "result": {"score": 1.0, "label": "good"},
                },
                {
                    "item": {
                        "text": "this movie sucks, it's the worst I have ever seen"
                    },
                    "result": {"score": 0.0, "label": "bad"},
                },
            ],
        },
    }
    ...

model_library = modelkit.ModelLibrary(models=[Tokenizer, Vectorizer, Classifier])
classifier_deprecated = model_library.get("imdb_classifier")
classifier_SOTA = model_library.get("imdb_classifier_SOTA")
```

As you can see, the `CONFIGURATIONS` map and the dependency renaming helped make this task easier than we may have thought in the first instance.

Also, the `tests_cases` are now part of each individual configuration so that to test each one independently.

