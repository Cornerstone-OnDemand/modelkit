
## Using `modelkit` models

The first thing you will want to do with a `Model` is get predictions from it. There are three ways to do so.

Let us consider this example, in which we have implemented `_predict`

```python
class MyModel(Model):
    def _predict(self, item, **kwargs):
        return item, kwargs
```

### Predictions for single items


Predictions for a single item can be obtained by calling the object, or it's `predict` function.

```python
prediction = model(item) # or model.predict(item)
# returns item
```

This will call whichever one of `_predict` or `_predict_batch` was implemented in the `Model`.

!!! note
    Although you have implemented `_predict`, you need to call `predict` (no underscore) to get predictions. The difference between the two is where `modelkit`'s magic operates 😀

Note that keyword arguments will be passed all the way to the implemented `_predict`:

```python
prediction = model(item, some_kwarg=10) # or model.predict(item)
# returns item, {"some_kwargs": 10}
```


### Predictions for lists of items

Predictions for list of items can also easily be obtained by using `predict_batch`:

```python
items = [1,2,3,4]
predictions = model.predict_batch(items)
```

Here, `items` **must** be a `list` of items. `modelkit` will iterate on it and fetch predictions.

This will also call whichever one of `_predict` or `_predict_batch` was implemented in the `Model`, and pass `kwargs`. 


### Predictions from iterators

It is also possible to iterate through predictions with an iterator, which is convenient to avoid having to load all items to memory before getting predictions.

```python
def generate_items():
    ...
    yield item
for prediction in model.predict_gen(generate_items()):
     # use prediction
    ...
```

A typical use case is to iterate through the lines of a file, perform some processing and write it straight back to another file

Note that in the case in which `_predict_batch` is implemented, you may see speed ups if you have written vectorized code. See the documentation on [batching](batching.md) for more information
