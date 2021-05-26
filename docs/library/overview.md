## Overview

The main concepts in `modelkit` are `Model` and the `ModelLibrary`.

The `ModelLibrary` instantiates and configures `Model` objects
and keep track of them during execution.

`Model` objects can then be requested via `ModelLibrary.get`,
 and used to make predictions via `Model`.


The ML logic is written in each `Model`'s `predict` functions, typically inside a module.
