`modelkit` models are **composable**: a `Model` can depend on other `Model`s, and exploit their attributes and predictions.

The `ModelLibrary` ensures that whenever `_load` or the `_predict_*` function are called, these models are loaded and present in the `model_dependencies` dictionary:

For example your can set your model's configuration to have access to two other `Model` objects:

```python
class SomeModel(Model):
    CONFIGURATIONS = {
        "some_model": {
            "model_dependencies": {
                "sentence_piece_cleaner",
                "sentence_piece_vectorizer"
            }
        }
    }
    def _predict(self, item):
        # The `model_dependencies` attribute contains fully loaded dependent
        # models which can be used directly:
        cleaned = self.models_dependencies["sentence_piece_cleaner"].predict(item["text"])
        ...
```

### Renaming dependencies

In addition, it is possible to rename dependencies on the fly by providing a mapping to `model_dependencies`. This is useful in order to keep the same `predict` code, even though dependencies have changed:

```python
class SomeModel(Model):
    CONFIGURATIONS = {
        "some_model": {
            "model_dependencies": {
                "cleaner": "sentence_piece_cleaner",
            }
        },
        "some_model_2": {
            "model_dependencies": {
                "cleaner": "sentence_piece_cleaner_2
            }
        }
    }

    def _predict(self, item):
        # Will call `sentence_piece_cleaner` in the `some_model` model and
        # `sentence_piece_cleaner_2` in the `some_model_2` model
        return self.model_dependencies["cleaner"].predict(item)
```

### Dependencies in `load`

Whenever a model's `_load` method is called, `modelkit` guarantees that all dependent models are also loaded, such that the `model_dependencies` attribute is populated by completely loaded models too.

It is therefore possible to use the `model_dependencies` in the `_load` method too:

```python
class SomeModel(Model):
    CONFIGURATIONS = {
        "some_model": {
            "model_dependencies": {
                "sentence_piece_cleaner",
                "sentence_piece_vectorizer"
            }
        }
    }
    def _load(self, item):
        # The `model_dependencies` attribute contains fully loaded dependent
        # models which can be used directly:
        ...
```