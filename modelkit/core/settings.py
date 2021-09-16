from typing import Optional, Union

import pydantic


class TFServingSettings(pydantic.BaseSettings):
    enable: bool = pydantic.Field(False, env="MODELKIT_TF_SERVING_ENABLE")
    mode: str = pydantic.Field("rest", env="MODELKIT_TF_SERVING_MODE")
    host: str = pydantic.Field("localhost", env="MODELKIT_TF_SERVING_HOST")
    port: int = pydantic.Field(None, env="MODELKIT_TF_SERVING_PORT")

    @pydantic.validator("port")
    @classmethod
    def default_serving_port(cls, v, values):
        if not v:
            v = 8500 if values.get("mode") == "grpc" else 8501
        return v


class CacheSettings(pydantic.BaseSettings):
    cache_provider: Optional[str] = pydantic.Field(None, env="MODELKIT_CACHE_PROVIDER")


class RedisSettings(CacheSettings):
    host: str = pydantic.Field("localhost", env="MODELKIT_CACHE_HOST")
    port: int = pydantic.Field(6379, env="MODELKIT_CACHE_PORT")

    @pydantic.validator("cache_provider")
    def _validate_type(cls, v):
        if v != "redis":
            raise ValueError
        return v


class NativeCacheSettings(CacheSettings):
    implementation: str = pydantic.Field("LRU", env="MODELKIT_CACHE_IMPLEMENTATION")
    maxsize: int = pydantic.Field(128, env="MODELKIT_CACHE_MAX_SIZE")

    @pydantic.validator("cache_provider")
    def _validate_type(cls, v):
        if v != "native":
            raise ValueError
        return v


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


class LibrarySettings(pydantic.BaseSettings):
    lazy_loading: bool = pydantic.Field(False, env="MODELKIT_LAZY_LOADING")
    override_assets_dir: Optional[str] = pydantic.Field(
        None, env="MODELKIT_ASSETS_DIR_OVERRIDE"
    )
    enable_validation: bool = pydantic.Field(True, env="MODELKIT_ENABLE_VALIDATION")
    tf_serving: TFServingSettings = pydantic.Field(
        default_factory=lambda: TFServingSettings()
    )
    cache: Optional[Union[RedisSettings, NativeCacheSettings]] = pydantic.Field(
        default_factory=lambda: cache_settings()
    )

    class Config:
        env_prefix = ""
