<h1 align="center"> modelkit </h1>
<p align="center">
  <em>Python framework for production ML systems.</em>
</p>
    
---

<p align="center">
  <img src="https://img.shields.io/github/workflow/status/clustree/modelkit/CI/main" />
  <img src="docs/badges/tests.svg" />
  <img src="docs/badges/coverage.svg" />
  <img src="https://img.shields.io/pypi/v/modelkit" />
  <img src="https://img.shields.io/pypi/pyversions/modelkit" />
  <a href="https://clustree.github.io/modelkit/index.html"><img src="https://img.shields.io/badge/docs-latest-blue" /></a>
  <img src="https://img.shields.io/github/license/clustree/modelkit" />
</p>

`modelkit` is a Python framework meant to make your ML models robust, reusable and performant in all situations you need to use them.

It is meant to bridge the gap between the different uses of your algorithms. With `modelkit` you can ensure that the same exact code will run in production, on your machine, or on data processing pipelines.

## Quickstart

`modelkit` provides a straightforward and consistent way to wrap your prediction  code in a `Model` class:

```python
from modelkit import Model

class MyModel(Model):
    def _predict(self, item):
        # This is where your prediction logic goes, use any asset loaded by 
        # _load here
        ...
        return result
```

This will open the doors to all of `modelkit`'s best features:

- **composable** Models can depend on other models, and evaluate them however you need to
- **extensible** Models can rely on arbitrary supporting configurations files called _assets_ hosted on local or cloud object stores
- **type-safe** Models' inputs and outputs can be validated by [pydantic](https://pydantic-docs.helpmanual.io/), you get type annotations for your predictions and can catch errors with static type analysis tools during development.
- **async** Models support async and sync prediction functions. `modelkit` supports calling async code from sync code so you don't have to suffer from partially async code.
- **testable** Models carry their own unit test cases, and unit testing fixtures are available for [pytest](https://docs.pytest.org/en/6.2.x/)
- **fast to deploy** Models can be served in a single CLI call using [fastapi](https://fastapi.tiangolo.com/)

In addition, you will find that `modelkit` is:

- **simple** Use pip to install `modelkit`, it is just a Python library.
- **robust** Follow software development best practices: version and test all your configurations and artifacts.
- **customizable** Go beyond off-the-shelf models: custom processing, heuristics, business logic, different frameworks, etc.
- **framework agnostic** Bring your own framework to the table, and use whatever code or library you want. `modelkit` is not opinionated about how you build or train your models.
- **organized** Version and share you ML library and artifacts with others, as a Python package or as a service. Let others use and evaluate your models!
- **fast** Model predictions can be batched for speed (you define the batching logic) with minimal overhead.
- **fast to code** Just write the prediction logic and that's it. No cumbersome pre or postprocessing logic, branching options, etc... The boilerplate code is minimal and sensible.

## Installation

Install with `pip`:

```
pip install modelkit
```

## Documentation

Refer to the [documentation](https://clustree.github.io/modelkit/) for more information.
