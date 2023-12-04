from typing import Optional, Union

import pydantic
import pydantic_settings
from typing_extensions import Annotated


class ModelkitSettings(pydantic_settings.BaseSettings):
    """
    Custom pydantic settings needed to allow setting both:
    - the validation alias
    - the field name
    And to prioritize the field name over the environment variable name.
    It aims at replacing the deprecated, pydantic 1.*, `env` argument to `Field`.
    It requires the use of the `validation_alias` and AliasChoices arguments in
    the child class.

    Example:
        class ServingSettings(ModelkitSettings):
            enable: bool = pydantic.Field(
                False,
                validation_alias=pydantic.AliasChoices(
                    "enable",
                    "MODELKIT_TF_SERVING_ENABLE",
                ),
            )
        assert ServingSettings().enable is False
        assert ServingSettings(enable=True).enable is True

        os.environ["MODELKIT_TF_SERVING_ENABLE"] = "True"
        assert ServingSettings().enable is True
        assert ServingSettings(enable=False).enable is False

    """

    model_config = pydantic.ConfigDict(extra="ignore")


class TFServingSettings(ModelkitSettings):
    enable: bool = pydantic.Field(
        False,
        validation_alias=pydantic.AliasChoices("enable", "MODELKIT_TF_SERVING_ENABLE"),
    )
    mode: str = pydantic.Field(
        "rest",
        validation_alias=pydantic.AliasChoices("mode", "MODELKIT_TF_SERVING_MODE"),
    )
    host: str = pydantic.Field(
        "localhost",
        validation_alias=pydantic.AliasChoices("host", "MODELKIT_TF_SERVING_HOST"),
    )
    port: int = pydantic.Field(
        8501, validation_alias=pydantic.AliasChoices("port", "MODELKIT_TF_SERVING_PORT")
    )

    @pydantic.field_validator("port")
    @classmethod
    def default_serving_port(cls, v, values):
        if not v:
            v = 8500 if values.get("mode") == "grpc" else 8501
        return v


class CacheSettings(ModelkitSettings):
    cache_provider: Optional[str] = pydantic.Field(
        None,
        validation_alias=pydantic.AliasChoices(
            "cache_provider", "MODELKIT_CACHE_PROVIDER"
        ),
    )


class RedisSettings(CacheSettings):
    host: str = pydantic.Field(
        "localhost",
        validation_alias=pydantic.AliasChoices("host", "MODELKIT_CACHE_HOST"),
    )
    port: int = pydantic.Field(
        6379, validation_alias=pydantic.AliasChoices("port", "MODELKIT_CACHE_PORT")
    )


class NativeCacheSettings(CacheSettings):
    implementation: str = pydantic.Field(
        "LRU",
        validation_alias=pydantic.AliasChoices(
            "implementation", "MODELKIT_CACHE_IMPLEMENTATION"
        ),
    )
    maxsize: int = pydantic.Field(
        128,
        validation_alias=pydantic.AliasChoices("maxsize", "MODELKIT_CACHE_MAX_SIZE"),
    )


def cache_settings():
    s = CacheSettings()
    if s.cache_provider is None:
        return None
    try:
        return RedisSettings()
    except pydantic.ValidationError:
        pass
    try:
        return NativeCacheSettings()
    except pydantic.ValidationError:
        pass


def _get_library_settings_cache_provider(v: Optional[str]) -> str:
    if v is None:
        return "none"
    elif isinstance(v, dict):
        return v.get("cache_provider", "none")
    return getattr(v, "cache_provider", "none")


class LibrarySettings(ModelkitSettings):
    lazy_loading: bool = pydantic.Field(
        False,
        validation_alias=pydantic.AliasChoices("lazy_loading", "MODELKIT_LAZY_LOADING"),
    )
    override_assets_dir: Optional[str] = pydantic.Field(
        None,
        validation_alias=pydantic.AliasChoices(
            "override_assets_dir", "MODELKIT_ASSETS_DIR_OVERRIDE"
        ),
    )
    tf_serving: TFServingSettings = pydantic.Field(default_factory=TFServingSettings)
    cache: Annotated[
        Union[
            Annotated[RedisSettings, pydantic.Tag("redis")],
            Annotated[NativeCacheSettings, pydantic.Tag("native")],
            Annotated[None, pydantic.Tag("none")],
        ],
        pydantic.Discriminator(_get_library_settings_cache_provider),
    ] = pydantic.Field(
        default_factory=cache_settings,
        union_mode="left_to_right",
    )
    model_config = pydantic.ConfigDict(extra="allow")
