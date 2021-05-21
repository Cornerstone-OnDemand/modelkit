"""
ModelLibrary

Ask for model using get_model. Handle loading, refresh...
"""
import collections
import copy
import os
import re
import time
from types import ModuleType
from typing import Any, Dict, List, Mapping, Optional, Type, Union

import redis
from pydantic import ValidationError

import modelkit.assets
from modelkit.assets.manager import AssetsManager
from modelkit.assets.settings import AssetSpec
from modelkit.core.model import Model, _create_model_object
from modelkit.core.model_configuration import ModelConfiguration, configure, list_assets
from modelkit.core.settings import ServiceSettings
from modelkit.log import logger
from modelkit.utils.redis import RedisCacheException, check_redis


class ConfigurationNotFoundException(Exception):
    pass


class ModelLibrary:
    def __init__(
        self,
        settings: Optional[Union[Dict, ServiceSettings]] = None,
        assetsmanager_settings: Optional[dict] = None,
        configuration: Optional[
            Dict[str, Union[Dict[str, Any], ModelConfiguration]]
        ] = None,
        models: Optional[Union[ModuleType, Type, List]] = None,
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
            settings = ServiceSettings(**settings)
        self.settings = settings or ServiceSettings()
        self.assetsmanager_settings = assetsmanager_settings or {}
        self._override_assets_manager = None
        self._lazy_loading = self.settings.lazy_loading
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

        self.redis_cache = None
        if self.settings.enable_redis_cache:
            try:
                self.redis_cache = check_redis(
                    self.settings.cache_host, self.settings.cache_port
                )
            except (AssertionError, redis.ConnectionError):
                logger.error(
                    "Cannot ping redis instance",
                    cache_host=self.settings.cache_host,
                    port=self.settings.cache_port,
                )
                raise RedisCacheException(
                    "Cannot ping redis instance"
                    f"[cache_host={self.settings.cache_host}, "
                    f"port={self.settings.cache_port}]"
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
        if not self.settings.override_assetsmanager_prefix:
            return None

        if self._override_assets_manager is None:
            logger.info(
                "Instantiating Override AssetsManager", lazy_loading=self._lazy_loading
            )
            override_settings = copy.deepcopy(self.assetsmanager_settings)
            override_settings["remote_store"][
                "assetsmanager_prefix"
            ] = self.settings.override_assetsmanager_prefix
            self._override_assets_manager = AssetsManager(**override_settings)

        return self._override_assets_manager

    def get_model(self, name):
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
                self.models[name].deserialize_asset()
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

        start = time.monotonic()
        self._check_configurations(model_name)
        self._resolve_assets(model_name)
        self._load_model(model_name)
        logger.info(
            "model loaded",
            name=model_name,
            duration_ms=int(round((time.monotonic() - start) * 1000)),
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

        self.models[model_name] = _create_model_object(
            configuration.model_type,
            service_settings=self.settings,
            asset_path=self.assets_info[configuration.asset]["path"]
            if configuration.asset
            else None,
            model_dependencies=model_dependencies,
            model_settings=model_settings,
            configuration_key=model_name,
            redis_cache=self.redis_cache,
        )

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
        venv = "modelkit_{}_FILE".format(
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
        venv = "modelkit_{}_VERSION".format(
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
                    yield self.get_model(model_key), item, result


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
    return svc.get_model(model_name)


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
