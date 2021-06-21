Although we have only describe synchronous models so far, `modelkit` allows you to write asynchronous code in `Model` objects and use the exact same functionality as described.

To do so, simply subclass the `modelkit.AsyncModel` instead of `Model`.

```python
class SomeAsyncModel(AsyncModel):
    CONFIGURATIONS = {"async_model": {}}

    async def _predict(self, item, **kwargs):
        await asyncio.sleep(0)
        return item
```

Now, it is required to write the `_predict` or `_predict_batch` methods with `async def`, and you can use `await` expressions.

Similarly, the `predict` and `predict_batch` methods become async, and `predict_gen` is an async generator:


```python
m = SomeAsyncModel()

await m.predict(...)
await m.predict_batch(...)

async for res in m.predict_gen(...):
    ...
```

## Async and sync composition

To make it easy to have both synchronous and asynchronous models in the same prediction call stack, `modelkit` atttempts to detect which context it is in and tries to make asynchronous models available even in synchronous contexts.


### Sync in async

If you have an asynchronous `Model` that depends on a synchronous model, there is nothing to do, you can simply call it as usual
```
model_a (async) -depends-on-> model_b
```

In `model_b._predict` this causes no issues

```python
    async def _predict(self, item):
        ...
        something = self.model_dependencies["model_b"].predict(...)
        ...
        return ...
```

### Async in sync

The opposite situation wherein you call an asynchronous model in a synchronous context is more annoying:

```
model_a -depends-on-> model_b (async) 
```

Indeed, this code would be invalid since `predict` returns a coroutine
```python
    def _predict(self, item):
        ...
        something = self.model_dependencies["model_b"].predict(...)
        ...
        return ...
```

To work around this, when `modelkit` encounters an `AsyncModel` in a synchronous context, it will wrap it in a `WrappedAsyncModel` that exposes "syncified" versions of the `predict` functions using [asgiref](https://github.com/django/asgiref).

As a result, the `model_a` will have a different object in its dependency, making the following valid.
```python
    def _predict(self, item):
        ...
        assert isinstance(self.model_dependencies["model_b"], WrappedAsyncModel)
        something = self.model_dependencies["model_b"].predict(...)
        ...
        return ...
```

TL;DR, if you want to use asynchronous logic in the `modelkit` code, make sure that your dependencies do not have a `sync-with-async-dependency` in the chain, otherwise this may create issues.