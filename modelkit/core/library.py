"""
ModelLibrary

Ask for model using get. Handle loading, refresh...
"""
import collections
import os
import re
from typing import (
    Any,
    Dict,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

import humanize
import pydantic
import redis
from asgiref.sync import AsyncToSync
from rich.console import Console
from rich.tree import Tree
from structlog import get_logger

import modelkit.assets
from modelkit.assets.manager import AssetsManager
from modelkit.assets.settings import AssetSpec
from modelkit.core import errors
from modelkit.core.model import Asset, AsyncModel, Model
from modelkit.core.model_configuration import ModelConfiguration, configure, list_assets
from modelkit.core.settings import LibrarySettings, NativeCacheSettings, RedisSettings
from modelkit.core.types import LibraryModelsType
from modelkit.utils.cache import Cache, NativeCache, RedisCache
from modelkit.utils.memory import PerformanceTracker
from modelkit.utils.pretty import describe
from modelkit.utils.redis import RedisCacheException

logger = get_logger(__name__)


class ConfigurationNotFoundException(Exception):
    pass


T = TypeVar("T", bound=Model)


class AssetInfo(pydantic.BaseModel):
    path: str
    version: Optional[str]


class ModelLibrary:
    def __init__(
        self,
        settings: Optional[Union[Dict, LibrarySettings]] = None,
        assetsmanager_settings: Optional[dict] = None,
        configuration: Optional[
            Dict[str, Union[Dict[str, Any], ModelConfiguration]]
        ] = None,
        models: Optional[LibraryModelsType] = None,
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
        self.settings: LibrarySettings = settings or LibrarySettings()
        self.assetsmanager_settings: Dict[str, Any] = assetsmanager_settings or {}
        self._override_assets_manager: Optional[AssetsManager] = None
        self._lazy_loading: bool = self.settings.lazy_loading
        if models is None:
            models = os.environ.get("MODELKIT_DEFAULT_PACKAGE")
        self.configuration: Dict[str, ModelConfiguration] = configure(
            models=models, configuration=configuration
        )
        self.models: Dict[str, Asset] = {}
        self.assets_info: Dict[str, AssetInfo] = {}
        self._assets_manager: Optional[AssetsManager] = None

        required_models = (
            required_models
            if required_models is not None
            else {r: {} for r in self.configuration}
        )
        if isinstance(required_models, list):
            required_models = {r: {} for r in required_models}
        self.required_models: Dict[str, Dict[str, Any]] = required_models
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
    def assets_manager(self):
        if self._assets_manager is None:
            logger.info("Instantiating AssetsManager", lazy_loading=self._lazy_loading)
            self._assets_manager = AssetsManager(**self.assetsmanager_settings)
        return self._assets_manager

    @property
    def override_assets_manager(self):
        if not self.settings.override_assets_dir:
            return None

        if self._override_assets_manager is None:
            logger.info(
                "Instantiating Override AssetsManager", lazy_loading=self._lazy_loading
            )
            self._override_assets_manager = AssetsManager(
                assets_dir=self.settings.override_assets_dir
            )
            self._override_assets_manager.storage_provider = None

        return self._override_assets_manager

    def get(self, name, model_type: Optional[Type[T]] = None) -> T:
        """
        Get a model by name

        :param name: The name of the required model
        :return: required model
        """

        if self._lazy_loading:
            # When in lazy mode ensure the model object and its dependencies
            # are instantiated, this will download the asset
            if name not in self.models:
                self._load(name)
            # Ensure that it is loaded
            if not self.models[name]._loaded:
                self.models[name].load()

        if name not in self.models:
            raise errors.ModelsNotFound(
                f"Model `{name}` not loaded."
                + (
                    f" (loaded models: {', '.join(self.models)})."
                    if self.models
                    else "."
                )
            )
        m = self.models[name]
        if model_type and not isinstance(m, model_type):
            raise ValueError(f"Model `{m}` is not an instance of {model_type}")
        return cast(T, m)

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
            time=humanize.naturaldelta(m.time, minimum_unit="seconds"),
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
        logger.debug("Loading model", model_name=model_name)
        if model_name in self.models:
            logger.debug("Model already loaded", model_name=model_name)
            return

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

        logger.debug("Instantiating Model object", model_name=model_name)
        self.models[model_name] = configuration.model_type(
            asset_path=self.assets_info[configuration.asset].path
            if configuration.asset
            else "",
            model_dependencies=model_dependencies,
            service_settings=self.settings,
            model_settings=model_settings or {},
            configuration_key=model_name,
            cache=self.cache,
        )
        logger.debug("Done loading Model", model_name=model_name)

    def _resolve_assets(self, model_name):
        """
        This function fetches assets for the current model and its dependent models
        and populates the assets_info dictionary with the paths.
        """
        logger.debug("Resolving asset for Model", model_name=model_name)
        configuration = self.configuration[model_name]
        # First, resolve assets from dependent models
        for dep_name in configuration.model_dependencies.values():
            self._resolve_assets(dep_name)

        if not configuration.asset:
            # If the model has no asset to load
            return

        model_settings = {
            **configuration.model_settings,
            **self.required_models.get(model_name, {}),
        }

        # If the asset is overriden in the model_settings
        if "asset_path" in model_settings:
            asset_path = model_settings.pop("asset_path")
            logger.debug(
                "Overriding asset from Model settings",
                model_name=model_name,
                asset_path=asset_path,
            )
            self.assets_info[configuration.asset] = AssetInfo(path=asset_path)

        asset_spec = AssetSpec.from_string(configuration.asset)

        # If the model's asset is overriden with environment variables
        venv = "MODELKIT_{}_FILE".format(
            re.sub(r"[\/\-\.]+", "_", asset_spec.name).upper()
        )
        local_file = os.environ.get(venv)
        if local_file:
            logger.debug(
                "Overriding asset from environment variable",
                asset_name=asset_spec.name,
                path=local_file,
            )
            self.assets_info[configuration.asset] = AssetInfo(path=local_file)

        # The assets should be retrieved
        # possibly override version
        venv = "MODELKIT_{}_VERSION".format(
            re.sub(r"[\/\-\.]+", "_", asset_spec.name).upper()
        )
        version = os.environ.get(venv)
        if version:
            logger.debug(
                "Overriding asset version from environment variable",
                asset_name=asset_spec.name,
                path=local_file,
            )
            asset_spec = AssetSpec.from_string(asset_spec.name + ":" + version)

        if self.override_assets_manager:
            try:
                self.assets_info[configuration.asset] = AssetInfo(
                    **self.override_assets_manager.fetch_asset(
                        spec=AssetSpec(
                            name=asset_spec.name, sub_part=asset_spec.sub_part
                        ),
                        return_info=True,
                    )
                )
                logger.debug(
                    "Asset has been overriden",
                    name=asset_spec.name,
                )
            except modelkit.assets.errors.AssetDoesNotExistError:
                logger.debug(
                    "Asset not found in overriden prefix",
                    name=asset_spec.name,
                )

        if configuration.asset not in self.assets_info:
            self.assets_info[configuration.asset] = AssetInfo(
                **self.assets_manager.fetch_asset(asset_spec, return_info=True)
            )

    def preload(self):
        # make sure the assets_manager is instantiated
        self.assets_manager
        for model_name in self.required_models:
            self._load(model_name)

    def close(self):
        for model in self.models.values():
            if isinstance(model, Model):
                model.close()
            if isinstance(model, AsyncModel):
                AsyncToSync(model.close)()

    async def aclose(self):
        for model in self.models.values():
            if isinstance(model, Model):
                model.close()
            if isinstance(model, AsyncModel):
                await model.close()

    def describe(self, console=None) -> None:
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
    models: Optional[LibraryModelsType] = None,
    model_type: Optional[Type[T]] = None,
) -> T:
    """
    Loads an modelkit model without the need for a ModelLibrary.
    This is useful for development, and should be avoided in production
    code.
    """
    lib = ModelLibrary(
        required_models=[model_name],
        models=models,
        configuration=configuration,
        settings={"lazy_loading": True},
    )
    return lib.get(model_name, model_type=model_type)


def download_assets(
    assetsmanager_settings: Optional[dict] = None,
    configuration: Optional[
        Mapping[str, Union[Dict[str, Any], ModelConfiguration]]
    ] = None,
    models: Optional[LibraryModelsType] = None,
    required_models: Optional[List[str]] = None,
) -> Tuple[Dict[str, Set[str]], Dict[str, AssetInfo]]:
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
            assets_info[asset] = AssetInfo(
                **assets_manager.fetch_asset(
                    asset,
                    return_info=True,
                )
            )
    return models_assets, assets_info
