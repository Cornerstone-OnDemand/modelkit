# Modelkit 0.1 migration note

Modelkit relies on `pydantic` as part of its validation process.

Modelkit 0.1 and onwards will be shipped with `pydantic 2`, which comes with __significant__ performance improvements at the cost of breaking changes.

Details on how to migrate to `pydantic 2` are available in the corresponding migration guide: https://docs.pydantic.dev/latest/migration/

### Installation
To install the brand new stable release of modelkit:
```
pip install modelkit --upgrade
```

### Known breaking changes

Some breaking changes are arising while upgrading to `pydantic 2` and the new `modelkit 0.1`. Here is a brief, rather exhaustive, list of the encountered issues or dropped features.

#### Drop: implicit pydantic model conversion

With `pydantic < 2` and `modelkit < 0.1`, the following pattern was authorized (even though not advised) due to implicit conversions between pydantic models:

```python
import modelkit
import pydantic
import typing

class OutputItem(pydantic.BaseModel):
    x: int

class AnotherOutputItem(pydantic.BaseModel):
    x: int

class MyModel(modelkit.Model[int, OutputItem]):
    def _predict(self, item):
        return AnotherOutputItem(x=item)

model = MyModel()
model(1)  # raises!

```

__This pattern is no longer allowed__.

However, here are the fixes:
- directly build the right output `pydantic` Model (here: `OutputItem`)
- directly use dicts to benefit from the dict to model conversion from `pydantic` and `modelkit` (or via `.model_dump()`)

### Drop: model validation deactivation

The `MODELKIT_ENABLE_VALIDATION` environment variable (or the `enable_validation` parameter of the `LibrarySettings`) which allowed one to deactivate validation if set to `False` was removed.

This feature has worked for `pydantic < 2` for rather simple `pydantic models` but not complex ones with nested structures (see: https://github.com/Cornerstone-OnDemand/modelkit/pull/8). However, it still is an open question in `pydantic 2`, whether to allow recursive construction of models without validation (see: https://github.com/pydantic/pydantic/issues/8084).
Due to the fact `pydantic 2` brings heavy performance improvements, this feature has not been re-implemented.

Fixes: None, just prepare to have your inputs / outputs validated :)

### Development Workflows

`modelkit 0.1` (and forward) changes will be pushed to the main branch.

For projects that have not migrated, `modelkit 0.0` will continue to receive maintenance on the `v0.0-maintenance` branch. Releases on PyPI and manual tags will adhere to the usual process.

To prevent your project from automatically upgrading to the new modelkit 0.1 upon its stable release, you can enforce an upper bound constraint in your requirements, e.g.: `modelkit<0.1`