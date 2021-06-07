"""
ModelLibrary

Ask for model using get. Handle loading, refresh...
"""
import collections
import copy
import os
import re
from types import ModuleType
from typing import Any, Dict, List, Mapping, Optional, Type, Union

import humanize
from pydantic import ValidationError
from rich.console import Console
from rich.tree import Tree
from structlog import get_logger

import modelkit.assets
from modelkit.assets.manager import AssetsManager
from modelkit.assets.settings import AssetSpec
from modelkit.core.model import Model
from modelkit.core.model_configuration import ModelConfiguration, configure, list_assets
from modelkit.core.settings import LibrarySettings, NativeCacheSettings, RedisSettings
from modelkit.utils.cache import Cache, NativeCache, RedisCache
from modelkit.utils.memory import PerformanceTracker
from modelkit.utils.pretty import describe
from modelkit.utils.redis import RedisCacheException

logger = get_logger(__name__)

try:
    import redis
except ImportError:
    logger.debug("Redis is not available " "(install modelkit[redis] or redis)")


class ConfigurationNotFoundException(Exception):
    pass


class ModelLibrary:
    def __init__(
        self,
        settings: Optional[Union[Dict, LibrarySettings]] = None,
        assetsmanager_settings: Optional[dict] = None,
        configuration: Optional[
            Dict[str, Union[Dict[str, Any], ModelConfiguration]]
        ] = None,
        models: Optional[Union[ModuleType, Type, List, str]] = None,
        required_models: Optional[Union[List[str], Dict[str, Any]]] = None,
    ):
        """
        Create a prediction service

        :param models: a `Model` class, a module, or a list of either in which the
        ModelLibrary will look for configurations.
        :param configuration: used to override configurations obtained from `models`
        :param required_models: used to restrict the models that are preloaded.
        :type settings: dict of additional settings (lazy_loading, etc.)
        :param assetsmanager_settings: settings passed to the AssetsManager
        """
        if isinstance(settings, dict):
            settings = LibrarySettings(**settings)
        self.settings = settings or LibrarySettings()
        self.assetsmanager_settings = assetsmanager_settings or {}
        self._override_assets_manager = None
        self._lazy_loading = self.settings.lazy_loading
        if models is None:
            models = os.environ.get("MODELKIT_DEFAULT_PACKAGE")
        self.configuration = configure(models=models, configuration=configuration)
        self.models: Dict[str, Model] = {}
        self.assets_info: Dict[str, Dict[str, str]] = {}
        self._asset_manager = None

        self.required_models = (
            required_models
            if required_models is not None
            else {r: {} for r in self.configuration}
        )
        if isinstance(self.required_models, list):
            self.required_models = {r: {} for r in self.required_models}

        self.cache: Optional[Cache] = None
        if self.settings.cache:
            if isinstance(self.settings.cache, RedisSettings):
                try:
                    self.cache = RedisCache(
                        self.settings.cache.host, self.settings.cache.port
                    )
                except (ConnectionError, redis.ConnectionError):
                    logger.error(
                        "Cannot ping redis instance",
                        cache_host=self.settings.cache.host,
                        port=self.settings.cache.port,
                    )
                    raise RedisCacheException(
                        "Cannot ping redis instance"
                        f"[cache_host={self.settings.cache.host}, "
                        f"port={self.settings.cache.port}]"
                    )
            if isinstance(self.settings.cache, NativeCacheSettings):
                self.cache = NativeCache(
                    self.settings.cache.implementation, self.settings.cache.maxsize
                )

        if not self._lazy_loading:
            self.preload()

    @property
    def asset_manager(self):
        if self._asset_manager is None:
            try:
                logger.info(
                    "Instantiating AssetsManager", lazy_loading=self._lazy_loading
                )
                self._asset_manager = AssetsManager(**self.assetsmanager_settings)
            except ValidationError:
                logger.info("No assets manager available")
        return self._asset_manager

    @property
    def override_assets_manager(self):
        if not self.settings.override_storage_prefix:
            return None

        if self._override_assets_manager is None:
            logger.info(
                "Instantiating Override AssetsManager", lazy_loading=self._lazy_loading
            )
            override_settings = copy.deepcopy(self.assetsmanager_settings)
            override_settings["remote_store"][
                "storage_prefix"
            ] = self.settings.override_storage_prefix
            self._override_assets_manager = AssetsManager(**override_settings)

        return self._override_assets_manager

    def get(self, name):
        """
        Get a model by name

        :param name: The name of the required model
        :return: required model
        """
        try:
            if not self._lazy_loading:
                return self.models[name]
            if name not in self.models:
                self._load(name)
            if not self.models[name]._loaded:
                self.models[name].load()
            return self.models[name]
        except KeyError:
            raise KeyError(
                f"Model `{name}` not loaded."
                + (
                    f" (loaded models: {', '.join(self.models)})."
                    if self.models
                    else "."
                )
            )

    def _load(self, model_name):
        """
        This function loads a configured model by name.
        """

        with PerformanceTracker() as m:
            self._check_configurations(model_name)
            self._resolve_assets(model_name)
            self._load_model(model_name)
        logger.info(
            "Model and dependencies loaded",
            name=model_name,
            time=humanize.naturaldelta(m.time, minimum_unit="microseconds"),
            time_s=m.time,
            memory=humanize.naturalsize(m.increment)
            if m.increment is not None
            else None,
            memory_bytes=m.increment,
        )

    def _check_configurations(self, configuration_key):
        if configuration_key not in self.configuration:
            logger.error(
                "Cannot find model configuration", name=configuration_key, sentry=True
            )

            candidates = {x: collections.Counter(x) for x in self.configuration}
            configuration = collections.Counter(configuration_key)
            differences = sorted(
                (
                    sum(x for x in (configuration - candidate).values())
                    + sum(x for x in (candidate - configuration).values()),
                    key,
                )
                for key, candidate in candidates.items()
            )
            msg = (
                f"Cannot resolve assets for model `{configuration_key}`: "
                "configuration not found.\n\n"
                f"Configured models: {', '.join(sorted(self.configuration))}.\n\n"
            )

            if differences and differences[0] and differences[0][0] < 10:
                msg += f'Did you mean "{differences[0][1]}" ?\n'

            raise ConfigurationNotFoundException(msg)

        configuration = self.configuration[configuration_key]
        for dep_name in configuration.model_dependencies.values():
            self._check_configurations(dep_name)

    def _load_model(self, model_name, model_settings=None):
        """
        This function loads dependent models for the current models, populating
        the _models dictionary with the instantiated model objects.
        """
        configuration = self.configuration[model_name]

        # First, load dependent predictors and add them to the model
        model_dependencies = {}
        for dep_ref_name, dep_name in configuration.model_dependencies.items():
            if dep_name not in self.models:
                self._load_model(dep_name)
            model_dependencies[dep_ref_name] = self.models[dep_name]

        model_settings = {
            **configuration.model_settings,
            **self.required_models.get(model_name, {}),
        }

        self.models[model_name] = configuration.model_type(
            asset_path=self.assets_info[configuration.asset]["path"]
            if configuration.asset
            else "",
            model_dependencies=model_dependencies,
            service_settings=self.settings,
            model_settings=model_settings or {},
            configuration_key=model_name,
            cache=self.cache,
        )
        if not self.settings.lazy_loading:
            self.models[model_name].load()

    def _resolve_assets(self, configuration_key):
        """
        This function fetches assets for the current model and its dependent models
        and populates the assets_info dictionary with the paths.
        """
        configuration = self.configuration[configuration_key]
        # First, resolve assets from dependent models
        for dep_name in configuration.model_dependencies.values():
            self._resolve_assets(dep_name)

        if not configuration.asset:
            # If the model has no asset to load
            return

        model_settings = {
            **configuration.model_settings,
            **self.required_models.get(configuration_key, {}),
        }

        # If the asset is overriden in the model_settings
        if "asset_path" in model_settings:
            self.assets_info[configuration.asset] = {
                "path": model_settings.pop("asset_path")
            }

        asset_spec = AssetSpec.from_string(configuration.asset)

        # If the model's asset is overriden with environment variables
        venv = "MODELKIT_{}_FILE".format(
            re.sub(r"[\/\-\.]+", "_", asset_spec.name).upper()
        )
        local_file = os.environ.get(venv)
        if local_file:
            logger.info(
                "Overriding asset from env variable",
                asset_name=asset_spec.name,
                path=local_file,
            )
            self.assets_info[configuration.asset] = {"path": local_file}

        # The assets should be retrieved
        # possibly override version
        venv = "MODELKIT_{}_VERSION".format(
            re.sub(r"[\/\-\.]+", "_", asset_spec.name).upper()
        )
        version = os.environ.get(venv)
        if version:
            asset_spec = AssetSpec.from_string(asset_spec.name + ":" + version)

        try:
            if self.override_assets_manager:
                self.assets_info[
                    configuration.asset
                ] = self.override_assets_manager.fetch_asset(
                    spec=AssetSpec(name=asset_spec.name, sub_part=asset_spec.sub_part),
                    return_info=True,
                )  # AssetSpec redefined to remove versions
                logger.info(
                    "Asset has been loaded with overriden prefix",
                    name=asset_spec.name,
                )
        except modelkit.assets.errors.ObjectDoesNotExistError:
            logger.debug(
                "Asset not found in overriden prefix",
                name=asset_spec.name,
            )
        if configuration.asset not in self.assets_info:
            self.assets_info[configuration.asset] = self.asset_manager.fetch_asset(
                asset_spec, return_info=True
            )

    def preload(self):
        # make sure the asset_manager is instantiated
        self.asset_manager
        for model_name in self.required_models:
            self._load(model_name)

    async def close_connections(self):
        for model in self.models.values():
            try:
                if model.aiohttp_session:
                    await model.aiohttp_session.close()
                    model.aiohttp_session = None
            except AttributeError:
                pass
            try:
                if model.requests_session:
                    model.requests_session.close()
                    model.requests_session = None
            except AttributeError:
                pass

    def _iterate_test_cases(self):
        model_types = {type(model_type) for model_type in self._models.values()}
        for model_type in model_types:
            for model_key, item, result in model_type._iterate_test_cases():
                if model_key in self._models:
                    yield self.get(model_key), item, result

    def describe(self, console=None):
        if not console:
            console = Console()
        t = Tree("[bold]Settings")
        console.print(describe(self.settings, t=t))
        t = Tree("[bold]Configuration")
        console.print(describe(self.configuration, t=t))
        t = Tree("[bold]Assets")
        if not self.assets_info:
            t.add("[dim][italic]No assets loaded")
        else:
            describe(self.assets_info, t=t)
        console.print(t)
        t = Tree("[bold]Models")
        if not self.models:
            t.add("[dim][italic]No models loaded")
        else:
            describe(self.models, t=t)
        console.print(t)


def load_model(
    model_name,
    configuration: Optional[
        Dict[str, Union[Dict[str, Any], ModelConfiguration]]
    ] = None,
    models: Optional[Union[ModuleType, Type, List]] = None,
):
    """
    Loads an modelkit model without the need for a ModelLibrary.
    This is useful for development, and should be avoided in production
    code.
    """
    svc = ModelLibrary(
        required_models=[model_name],
        models=models,
        configuration=configuration,
        settings={"lazy_loading": True},
    )
    return svc.get(model_name)


def download_assets(
    assetsmanager_settings: Optional[dict] = None,
    configuration: Optional[
        Mapping[str, Union[Dict[str, Any], ModelConfiguration]]
    ] = None,
    models: Optional[Union[ModuleType, Type, List]] = None,
    required_models: Optional[List[str]] = None,
):
    assetsmanager_settings = assetsmanager_settings or {}
    assets_manager = AssetsManager(**assetsmanager_settings)

    configuration = configure(models=models, configuration=configuration)

    models_assets = {}
    assets_info = {}

    required_models = required_models or [r for r in configuration]

    for model in required_models:
        models_assets[model] = list_assets(
            required_models=[model], configuration=configuration
        )
        for asset in models_assets[model]:
            if asset in assets_info:
                continue
            assets_info[asset] = assets_manager.fetch_asset(
                asset,
                return_info=True,
            )
    return models_assets, assets_info
