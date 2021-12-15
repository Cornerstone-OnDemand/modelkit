import importlib
import inspect
import os
import pkgutil
import re
from collections import ChainMap
from types import ModuleType
from typing import Any, Dict, List, Mapping, Optional, Set, Type, Union

import pydantic
from structlog import get_logger

from modelkit.core.model import Asset
from modelkit.core.types import LibraryModelsType

logger = get_logger(__name__)


class ModelConfiguration(pydantic.BaseSettings):
    model_type: Type[Asset]
    asset: Optional[str]
    model_settings: Optional[Dict[str, Any]] = {}
    model_dependencies: Optional[Dict[str, str]]

    @pydantic.validator("model_dependencies", always=True, pre=True)
    def validate_dependencies(cls, v):
        if not v:
            return {}
        if isinstance(v, (list, set)):
            return {key: key for key in v}
        return v


def walk_module_objects(mod, already_seen):
    for name, obj in inspect.getmembers(mod):
        if (
            inspect.isclass(obj)
            and issubclass(obj, Asset)
            and name not in {"Model", "Asset", "TensorflowModel"}
            and obj not in already_seen
        ):
            already_seen.add(obj)
            yield obj


def walk_objects(mod):
    already_seen = set()
    try:
        for _, modname, _ in pkgutil.walk_packages(mod.__path__, mod.__name__ + "."):
            submod = importlib.import_module(modname)
            yield from walk_module_objects(submod, already_seen)
    except AttributeError:
        yield from walk_module_objects(mod, already_seen)


TO_SNAKE_CASE_PATTERN = re.compile(r"(?<!^)(?=[A-Z])")


def to_snake_case(name):
    return TO_SNAKE_CASE_PATTERN.sub("_", name).lower()


def _configurations_from_objects(m) -> Dict[str, ModelConfiguration]:
    if inspect.isclass(m) and issubclass(m, Asset):
        configs = {}
        if m.CONFIGURATIONS:
            for key, config in m.CONFIGURATIONS.items():
                configs[key] = ModelConfiguration(**{**config, "model_type": m})
        else:
            configs[to_snake_case(m.__name__)] = ModelConfiguration(model_type=m)
        return configs
    elif isinstance(m, (list, tuple)):
        return dict(ChainMap(*(_configurations_from_objects(sub_m) for sub_m in m)))
    elif isinstance(m, ModuleType):
        configs = {}
        for m in walk_objects(m):
            if m.CONFIGURATIONS:
                for key, config in m.CONFIGURATIONS.items():
                    configs[key] = ModelConfiguration(**{**config, "model_type": m})
            else:
                configs[to_snake_case(m.__name__)] = ModelConfiguration(model_type=m)
        return configs
    elif isinstance(m, str):
        models = [importlib.import_module(modname) for modname in m.split(",")]
        return _configurations_from_objects(models)
    else:
        raise ValueError(f"Don't know how to configure {m}")


def configure(
    models: Optional[LibraryModelsType] = None,
    configuration: Optional[
        Mapping[str, Union[Dict[str, Any], ModelConfiguration]]
    ] = None,
) -> Dict[str, ModelConfiguration]:
    if not models:
        models = os.environ.get("MODELKIT_DEFAULT_PACKAGE")

    conf = _configurations_from_objects(models) if models else {}
    if configuration:
        for key in set(conf.keys()) & set(configuration.keys()):
            if key in configuration:
                # We extract configuration[key] in a variable to help mypy infer correct
                # type after isinstance checks
                conf_value = configuration[key]
                if isinstance(conf_value, ModelConfiguration):
                    conf[key] = conf_value
                elif isinstance(conf_value, dict):
                    conf[key] = ModelConfiguration(**{**conf[key].dict(), **conf_value})
        for key in set(configuration.keys()) - set(conf.keys()):
            conf_value = configuration[key]
            if isinstance(conf_value, ModelConfiguration):
                conf[key] = conf_value
            elif isinstance(conf_value, dict):
                conf[key] = ModelConfiguration(**conf_value)
    return conf


def list_assets(
    models: Optional[LibraryModelsType] = None,
    required_models: Optional[List[str]] = None,
    configuration: Optional[
        Mapping[str, Union[Dict[str, Any], ModelConfiguration]]
    ] = None,
) -> Set[str]:
    merged_configuration = configure(models=models, configuration=configuration)
    assets: Set[str] = set()
    for model in required_models or merged_configuration.keys():
        model_configuration = merged_configuration[model]
        if model_configuration.asset:
            assets.add(model_configuration.asset)
        if model_configuration.model_dependencies:
            assets |= list_assets(
                configuration=merged_configuration,
                required_models=list(model_configuration.model_dependencies.values()),
            )
    return assets
