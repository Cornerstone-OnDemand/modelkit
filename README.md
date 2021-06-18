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
- **async** Models support async and synchronous prediction functions

The philoshy:

- **a clear focus on ML inference/prediction services** ModelKit is not meant to tool ML activities as data mining, model exploration (design, feature engineering) or model evaluation. Our framework is meant for production-ready ML models and focus the robustness, reusability and technical performance of their related prediction services.
- **as simple and transparent as possible** No magic auto-deployment of model into production, no modelKit UI with workflows or internal states. This is just a python framework to organize your model code and build related apis.
- **meant for custom models** ModelKit find its strength if you need to go beyond off-the-shelf models: python custom processings, inter-dependencies to other custom models, custom "batch predict" implementations, custom model configurations...
- **meant to follow software development good practices** every code and configuration will be on your git, models are meant to be tested in git and versionned on file stores, related services are created with specific list of models in input to allow RAM/CPU optimization, etc.
- **meant to easily share your models with others** As ModelKit models can be easily shared as python package or api, this is a powerful way to let other people or teams use your model and deploy them in production if needed

## Installation

Install with `pip`:

```
pip install modelkit
```

## Documentation

Refer to the [documentation](https://clustree.github.io/modelkit/) for more information.
