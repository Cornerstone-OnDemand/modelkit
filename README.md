<h1 align="center"> modelkit </h1>
<p align="center">
  <em>Python framework for production ML systems.</em>
</p>
    
---

`modelkit` is a Python framework to maintain and run machine learning (ML) code in production environments.

The key features are:

- **type-safe** Models' inputs and outputs can be validated by [pydantic](https://pydantic-docs.helpmanual.io/)
- **composable** Models are *composable*: they can depend on other models. 
- **organized** Store and share your models as regular Python packages.
- **extensible** Models can rely on arbitrary supporting configurations files called *assets* hosted on local or cloud object stores
- **testable** Models carry their own unit test cases, and unit testing fixtures are available for [pytest](https://docs.pytest.org/en/6.2.x/)
- **fast to code** Models can be served in a single CLI call using [fastapi](https://fastapi.tiangolo.com/)
- **fast** Models' predictions can be batched for speed
- **async** Models support sync and synchronous prediction functions

## Installation

Install with `pip`:

```
pip install modelkit
```

## Documentation

Refer to the [documentation](https://clustree.github.io/modelkit/) for more information.

