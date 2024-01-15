<p align="center">
  <a href="https://github.com/cornerstone-ondemand/modelkit">
    <img src="https://raw.githubusercontent.com/cornerstone-ondemand/modelkit/main/.github/resources/logo.svg" alt="Logo" width="80" height="80">
</a>
</p>
<h1 align="center"> modelkit </h1>
<p align="center">
  <em>Python framework for production ML systems.</em>
</p>

---

<p align="center">
  <a href="https://github.com/Cornerstone-OnDemand/modelkit/actions/workflows/tests.yml?query=branch%3Amain"><img src="https://img.shields.io/github/actions/workflow/status/cornerstone-ondemand/modelkit/tests.yml?branch=main" /></a>
  <a href="https://pypi.org/project/modelkit/"><img src="https://img.shields.io/pypi/v/modelkit" /></a>
  <a href="https://pypi.org/project/modelkit/"><img src="https://img.shields.io/pypi/pyversions/modelkit" /></a>
  <a href="https://cornerstone-ondemand.github.io/modelkit/index.html"><img src="https://img.shields.io/badge/docs-latest-blue" /></a>
  <a href="https://github.com/cornerstone-ondemand/modelkit/blob/main/LICENSE"><img src="https://img.shields.io/github/license/cornerstone-ondemand/modelkit" /></a>
  <a href="https://pepy.tech/project/modelkit"><img src="https://pepy.tech/badge/modelkit" /></a>
  <a href="https://github.com/Cornerstone-OnDemand/modelkit/graphs/contributors"><img src="https://img.shields.io/github/contributors/Cornerstone-OnDemand/modelkit" /></a>
</p>

`modelkit` is a minimalist yet powerful MLOps library for Python, built for people who want to deploy ML models to production.

It packs several features which make your go-to-production journey a breeze, and ensures that the same exact code will run in production, on your machine, or on data processing pipelines.

## Quickstart

`modelkit` provides a straightforward and consistent way to wrap your prediction  code in a `Model` class:

```python
from modelkit import Model

class MyModel(Model):
    def _predict(self, item):
        # This is where your prediction logic goes
        ...
        return result
```

Be sure to check out our tutorials in the [documentation](https://cornerstone-ondemand.github.io/modelkit/).

## Features

Wrapping your prediction code in `modelkit` instantly gives acces to all features:

- **fast** Model predictions can be batched for speed (you define the batching logic) with minimal overhead.
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
- **fast to code** Just write the prediction logic and that's it. No cumbersome pre or postprocessing logic, branching options, etc... The boilerplate code is minimal and sensible.

## Installation

Install the latest stable release with `pip`:

```
pip install modelkit
```

Optional dependencies are available for remote storage providers ([see documentation](https://cornerstone-ondemand.github.io/modelkit/assets/storage_provider/#using-different-providers))

### 🚧 Beta release

`modelkit 0.1` and onwards will be shipped with `pydantic 2`, bringing significant performance improvements 🎉 ⚡

To try out the beta before it is stable:

```
pip install --pre modelkit
```

Also, you can refer to the [modelkit migration note](https://cornerstone-ondemand.github.io/modelkit/migration.md)
 to ease the migration process!

## Community
Join our [community](https://discord.gg/ayj5wdAArV) on Discord to get support and leave feedback

### Local install

Contributors, if you want to install and test locally:

```
# install
make setup

# lint & test
make tests
```
