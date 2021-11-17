# Versioning

2 versioning systems are implemented by default in the `modelkit/assets/versioning` repository :

- `major_minor` (used by default)
- `simple_date`

We can implement a new versioning system by inheriting from the `AssetsVersioningSystem` class and
override several methods which are necessary for the system to function.

To use a specific system use the environment variable `MODELKIT_ASSETS_VERSIONING_SYSTEM`

## AssetsVersioningSystem

Some abstract functions have to be overriden :

- `get_initial_version` which returns the initial version of a new asset.

- `check_version_valid` which checks if a given version is valid.

- `sort_versions` which implements the sorting logic of versions (used for example to get the latest version).

- `increment_version` which implements the version incrementation logic.

- `get_update_cli_params` which specifies the  `update cli` display and the `increment_version` params received from parameters given to the `update cli`.

other methods can be overriden if needed.

- `is_version_complete` returns `True` by default but can be overriden for system which allows
incomplete version to specify if a given is complete or not.

- `get_latest_partial_version` returns the last version by default but can be overriden for system
which allow incomplete version to filter versions corresponding to a given incomplete version.


## Simple Date

Simple date is a very simple versioning system using current date in UTC ISO 8601 Z format as version :
 `YYYY-MM-DDThh-mm-ssZ` (due to filename constraints the `:` of `hh:mm:ss` in the original notation are replaced with `-` ).

`get_initial_version` returns the current date in UTC iso format.

`increment_version` returns the current date in UTC iso format.

`sort_versions` iso format is compatible with a reversed alpha-numerical order.


## Major / Minor (default)

The major / minor system uses a `x.y` format where `x` is the `major` and `y` the `minor` version.

`get_initial_version` returns `0.0`.

`increment_version` increments the `minor` version (`y+=1`). A `bump_version` parameter allow us to increment a new `major` version  (`x+=1 ; y=0`).

`sort_versions` sorts according to a `(major, minor)` key, considering `major` and `minor` as integers.


major/minor is compatible with incomplete versioning : version `x` corresponds to the latest `x.y` version :

`is_version_complete` returns `True` if `major` AND `minor` are specified and `False` if only the `major` is specified.

`get_latest_partial_version` returns the latest version OR the latest `x.y` version for a specified major `x`.

