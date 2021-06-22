`modelkit` centralizes all of your models in a single object, which makes it easy to serve as a REST API via an HTTP server.

Of course, you can do so using your favourite framework, ours is [fastapi](https://fastapi.tiangolo.com/), so we have integrated several methods to make it easy to serve your models _directly_ with it.

### Using uvicorn

A single CLI call will expose your models using `uvicorn`:

```bash
modelkit serve PACKAGE --required-models REQUIRED_MODELS --host HOST --port PORT
```

This will create a server with a single worker with all the models listed in `REQUIRED_MODELS`, as configured in the `PACKAGE`.

Each `Model` configured as `model_name` will have two POST endpoints:

- `/predict/model_name` which accepts single items
- `/predict/batch/model_name` which accepts lists of items

Endpoint payloads and specs are parametrized by the `pydantic` payloads that it uses to validate its inputs and outputs. 

Head over to `/docs` to check out the swagger and try your models out!

### Using gunicorn with multiple workers

For more performance, `modelkit` allows you to use `gunicorn` with multiple workers that share the same `ModelLibrary`: `modelkit.api.create_modelkit_app`.

It can take all its arguments through environment variables, so you can run a server quickly, for example:

```bash
export MODELKIT_DEFAULT_PACKAGE=my_package
export PYTHONPATH=path/to/the/package
gunicorn \
    --workers 4 \
    --preload \
    --worker-class=uvicorn.workers.UvicornWorker \
    'modelkit.api:create_modelkit_app()'
```

!!! note
    Since `ModelLibrary` is shared between the workers, therefore adding workers will not increase the memory footprint.

### Automatic endpoints router in fastAPI

If you are interested in adding all `Model` endpoints in an existing `fastapi` application, you can also use the `modelkit.api.ModelkitAutoAPIRouter`:

```python
app = fastapi.FastAPI()
router = ModelkitAutoAPIRouter(
    required_models=required_models,
    models=models)
app.include_router(router)
```

Which will include one endpoint for each model in `required_models`, pulled form the `models` package.

To override the route paths for individual models, use `route_paths`:

```python
router = ModelkitAutoAPIRouter(
    required_models=required_models,
    models=models,
    route_paths={
        "some_model": "/a/new/path"
    }
)
```
