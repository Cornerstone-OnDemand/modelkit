Here is the entire tutorial implementation, covering most Modelkit's features to get you started.

```python
from typing import List, Optional

import modelkit
import numpy as np
import pydantic
import spacy
import tensorflow as tf


class Tokenizer(modelkit.Model[str, List[str]]):
    CONFIGURATIONS = {"imdb_tokenizer": {}}
    TEST_CASES = [
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
            "model_dependencies": {
                "tokenizer": "imdb_tokenizer",
                "vectorizer": "imdb_vectorizer",
            },
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
        self.tokenizer = self.model_dependencies["tokenizer"]
        self.vectorizer = self.model_dependencies["vectorizer"]

    def _predict_batch(self, reviews):
        texts = [review.text for review in reviews]
        tokenized_reviews = self.tokenizer.predict_batch(texts)
        vectorized_reviews = self.vectorizer.predict_batch(tokenized_reviews, length=64)
        predictions_scores = self.model.predict(vectorized_reviews)
        predictions = [
            {"score": score, "label": "good" if score >= 0.5 else "bad"}
            for score in predictions_scores
        ]
        return predictions


model_library = modelkit.ModelLibrary(models=[Tokenizer, Vectorizer, Classifier])
classifier = model_library.get("imdb_classifier")
prediction = classifier.predict({"text": "I love the main character"})
print(prediction.label)
```
