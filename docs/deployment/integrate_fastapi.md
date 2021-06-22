
Integrating `modelkit` models in an existing app is extremely simple, you simply have to add the `ModelLibrary` object to the main module.

### Instantiate a ModelLibrary

In the main Python script where you define your fastapi application, attach the model library to the application state:

```python
import fastapi
import modelkit

app = fastapi.FastAPI()
# instantiate the library
lib = modelkit.ModelLibrary(
    ...
)
# add the library to the app state
app.state.lib = lib


# Don't forget to close the connections when the application stops!
@app.on_event("shutdown")
async def shutdown_event():
    await app.state.lib.aclose()
```

??? "Multiple workers"
    This method of integrating the `ModelLibrary` ensures that all models are created before different workers are instantiated (e.g. using `gunicorn --preload`), which is convenient since all will share the same model objects and not increase memory.


### Use the models

Finally, anywhere else where you add endpoints to the application, you can retrieve the `ModelLibrary` from the `request` object.

Since getting the `Model` object is just a dictionary lookup, retrieving it is instantaneous.

```python
@app.post(...)
def some_path_endpoint(request: fastapi.Request, item):
    # Get the model object
    m = request.app.state.lib.get("model_name")
    # Use to make predictions as usual
    m.predict(...)
    ...
    return ...
```

??? "Async support"
    This is the context in which `modelkit`'s async support shines, be sure to use your `AsyncModel`s here:

    ```python
    @app.post(...)
    async def some_path_endpoint(request: fastapi.Request, item):
        m = request.app.state.lib.get("model_name")
        result = await m.predict(...)
        ...
        return ...
    ```

