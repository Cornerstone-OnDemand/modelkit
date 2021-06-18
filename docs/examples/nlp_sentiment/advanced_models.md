You have now seen most development features and how to implement everything from the Tokenizer to the Classifier.

Let's see how we can put it all together, while reviewing all Modelkit's features we have seen so far and introducing a powerful new feature: model dependencies.

## Composing models

`modelkit`'s allows you to add models as dependencies of other models, and use them in the `_predict` methods.

For example, it is desirable for our classifier to take string reviews as input, and output a class label ("good" or "bad"). This can be achieved using model dependencies.

We need to specify the `model_dependencies` key in the `CONFIGURATIONS` map to add the `Tokenizer` and the `Vectorizer` as dependencies:

```python
import modelkit

class Classifier(modelkit.Model[str, str]):
    CONFIGURATIONS = {
        "imdb_classifier": {
            "asset": "imdb_model.h5",
            "model_dependencies": {"imdb_tokenizer", "imdb_vectorizer"}
        },
    }
```

The `modelkit.ModelLibrary` will take care of loading the model dependencies  before your model is available. They are then made available in the `model_dependencies` attribute, and can readily be used in the `_predict` method.

For example:

```python
import modelkit

class Classifier(modelkit.Model[str, str]):
    CONFIGURATIONS = {
        "imdb_classifier": {
            "asset": "imdb_model.h5",
            "model_dependencies": {"imdb_tokenizer", "imdb_vectorizer"}
        },
    }
    ...
    def _predict_batch(self, reviews):
        # this looks like the previous end-to-end example from the previous section
        tokenized_reviews = self.model_dependencies["imdb_tokenizer"].predict_batch(reviews)
        vectorized_reviews = self.model_dependencies["imdb_vectorizer"].predict_batch(tokenized_reviews, length=64)
        predictions_scores = self.model.predict(vectorized_reviews)
        predictions_classes = ["good" if score >= 0.5 else "bad" for score in predictions_scores]
        return predictions_classes
```

This end-to-end classifier is much easier to use, and still loadable easily: let us use a `ModelLibrary`:

```python
# define the model library with all necessary models
model_library = modelkit.ModelLibrary(models=[Tokenizer, Vectorizer, Classifier])

# this will load all models
classifier = model_library.get("imdb_classifier")
classifier.predict("This movie is freaking awesome, I love the main character")
# good 
```
## Adding complex output

We may want to output the score as well as a class when using the model. 

Although we could return a dictionary, this can just as easily be achieved by outputing a Pydantic model, which offers more advanced validation features (and is used under the hood in `modelkit`), and can readily be used in fastapi endpoints.

This is really good practice, as it makes your code more understandable (even more so as your number of models grow).

Let us modify our code to specify a `pydantic.BaseModel` as the output of our `Model`, which contains a label and the score.

```python hl_lines="6-8 42"
import modelkit
import numpy as np
import pydantic
import tensorflow as tf

class MovieSentimentItem(pydantic.BaseModel):
    label: str
    score: float

class Classifier(modelkit.Model[str, MovieSentimentItem]):
    CONFIGURATIONS = {
        "imdb_classifier": {
            "asset": "imdb_model.h5",
            "model_dependencies": {"imdb_tokenizer", "imdb_vectorizer"},
        },
    }
    TEST_CASES = [
        {
            "item": {"text": "i love this film, it's the best I've ever seen"},
            "result": {"score": 0.8441019058227539, "label": "good"},
        },
        {
            "item": {"text": "this movie sucks, it's the worst I have ever seen"},
            "result": {"score": 0.1625385582447052, "label": "bad"},
        },
    ]

    def _load(self):
        self.model = tf.keras.models.load_model(self.asset_path)
        self.tokenizer = self.model_dependencies["imdb_tokenizer"]
        self.vectorizer = self.model_dependencies["imdb_vectorizer"]

    def _predict_batch(self, reviews):
        texts = [reviews.text for review in reviews]
        tokenized_reviews = self.tokenizer.predict_batch(texts)
        vectorized_reviews = self.vectorizer.predict_batch(tokenized_reviews, length=64)
        predictions_scores = self.model.predict(vectorized_reviews)
        return [
            {"score": score, "label": "good" if score >= 0.5 else "bad"}
            for score in predictions_scores
        ]
```

We also added some `TEST_CASES` to make sure that our model still behaves correctly.

!!! note
    Although we return a dictionary, it will be turned into a `MovieSentimentItem`, and validated by Pydantic.

We can now test the `Model`:

```python
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

## Multiple Model configurations

To conclude this tutorial, let us briefly see how to define multiple configurations, and why one would want to do that.

Assume that our `Classifier` model goes to production and most users are happy with it, but some are not. You start from scratch: redefine a tokenizer, vectorizer, train a new classifier with a different architecture and more data, and save it preciously.

Since you have always been the original guy in the room, all the new models now have a "_SOTA" suffix. You managed to keep the same inputs, outputs, pipeline architecture and made your process reproductible.

"That should do it !", you yell across the open space.

However, you probably do not want to surprise your clients with a new model without informing them before.Some might want to stick with the old one, while the unhappy ones would want to change ASAP.

Modelkit has got your back, and allows you to define multiple configurations while keeping the exact same code.

Here is how you go about doing this:

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
```

In order to use the same code within `_predict`, we have renamed the dependencies, by using a dictionary instead of a set in `model_dependencies`.

The `model_dependencies` attribute of `classifier` and `classifier_SOTA` will have the same `tokenizer` and `vectorizer` keys, but pointing to different `Model`s.
Also, the `tests_cases` are now part of each individual configuration so that to test each one independently.

Now both of your models are available through the same library:

```python
model_library = modelkit.ModelLibrary(models=[Tokenizer, Vectorizer, Classifier])
classifier_deprecated = model_library.get("classifier")
classifier_SOTA = model_library.get("classifier_SOTA")
```

Additionally, you can decide to filter out which one you are interested in (and avoid it being loaded in memory if it is unused), by specifying the `required_models` keyword argument:

```python
model_library = modelkit.ModelLibrary(
    required_models=["classifier_SOTA"]
    models=[Tokenizer, Vectorizer, Classifier]
)
```

As you can see, the `CONFIGURATIONS` map and the dependency renaming helped make this task easier than we may have thought in the first instance.

