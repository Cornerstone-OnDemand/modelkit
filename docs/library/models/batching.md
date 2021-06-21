
Oftentimes, when using external libraries, it is much faster to compute predictions with batches of items. This is true with deep learning, but also when writing code with libraries like `numpy`. 

For this reason, it is possible to define `Model` with batched prediction code, by overriding `_predict_batch` instead of `_predict`:

```python
class MyModel(Model):
    def _predict(self, item):
        return item
    # OR 
    def _predict_batch(self, items):
        return items
```

Whichever one you decide to implement, `modelkit` will still expose the same methods `predict`, `predict_batch` and `predict_gen`.

Typically, one would first implement `_predict` to get the logic right, and later, if needed, implement `_predict_batch` to improve performance.

!!! warning
    Don't override both `_predict` and `_predict_batch`. This will raise an error

??? optional-class "Example"
    In this example, we implement a dummy `Model` that computes the position
    of the min in a list using `np.argmin`. 

    In one version the code is not vectorized (it operates on a single item)
    and in the other one it is (a whole batched is processed at once).

    The vectorized version is ~50% faster
    ```python
    import random
    import timeit

    from modelkit.core.model import Model
    import numpy as np

    # Create some data
    data = []
    base_item = list(range(100))
    for _ in range(128):
        random.shuffle(base_item)
        data.append(list(base_item))

    # This model is not vectorized, `np.argmin`
    # will be called individually for each batch
    class MinModel(Model):
        def _predict(self, item):
            return np.argmin(item)


    m = MinModel()

    # This model is vectorized, `np.argmin`
    # is called over a whole batch
    class MinBatchedModel(Model):
        def _predict_batch(self, items):
            return np.argmin(items, axis=1)


    m_batched = MinBatchedModel()

    # They do return the same results
    assert m.predict_batch(data) == m_batched.predict_batch(data)


    # The batched model is ~50% slower
    timeit.timeit(lambda: m.predict_batch(data), number=1000)
    # The batched model is ~50% slower
    timeit.timeit(lambda: m_batched.predict_batch(data), number=1000)
    # Even more so with a larger batch size
    timeit.timeit(lambda: m_batched.predict_batch(data, batch_size=128), number=1000)
    ```

### Controling batch size

The default batch size for the `Model` object is controlled its `batch_size` attribute. It defaults to `None`, which means that `_predict_batch` will by default always get:

- a single, full length batch with all the items when called via `predict_batch`
- as many batches of size one as there are items when called via `predict_gen`

It is possible to control the batch size for each call to `_predict_batch`, by using:

```python
items = [1,2,3,4]
predictions = model.predict_batch(items, batch_size=2)
for p in model.predict_gen(iter(items), batch_size=2):
    ...
# predictions will be computed in batches of two
```

This is useful to avoid computing batches that are too large and may take up too much memory.

Note that, although `modelkit` will attempt to build batches of even size, this is not always the case:

- **remaining items** if you request 10 predictions with a batch size of 3, the last batch will only contain one
- **caching** when caching, `modelkit` will yield if sufficiently many predictions can be fetched in the cache, and compute the rest, wich will lead to smaller batches than expected.

If you do need to access the number of items in a batch, use `len(items)` inside the `_predict_batch`. If you need to make sure that it is contant, you will have to implement padding yourself.

!!! batches and iterators
    When using `predict_gen` with a model with `_predict_batch` implemented, `modelkit` will construct batches, while still yielding items one by one.
