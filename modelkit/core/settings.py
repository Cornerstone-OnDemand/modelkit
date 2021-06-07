from typing import Optional, Union

import pydantic


class TFServingSettings(pydantic.BaseSettings):
    enable: bool = pydantic.Field(False, env="ENABLE_TF_SERVING")
    mode: str = pydantic.Field("rest", env="TF_SERVING_MODE")
    host: str = pydantic.Field("localhost", env="TF_SERVING_HOST")
    port: int = pydantic.Field(None, env="TF_SERVING_PORT")

    @pydantic.validator("port")
    @classmethod
    def default_serving_port(cls, v, values):
        if not v:
            v = 8500 if values.get("mode") == "grpc" else 8501
        return v


class CacheSettings(pydantic.BaseSettings):
    cache_provider: Optional[str] = pydantic.Field(None, env="CACHE_PROVIDER")


class RedisSettings(CacheSettings):
    host: str = pydantic.Field("localhost", env="CACHE_HOST")
    port: int = pydantic.Field(6379, env="CACHE_PORT")

    @pydantic.validator("cache_provider")
    def _validate_type(cls, v):
        if v != "redis":
            raise ValueError
        return v


class NativeCacheSettings(CacheSettings):
    implementation: str = pydantic.Field("LRU", env="CACHE_IMPLEMENTATION")
    maxsize: int = pydantic.Field(128, env="CACHE_MAX_SIZE")

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
    lazy_loading: bool = pydantic.Field(False, env="LAZY_LOADING")
    async_mode: bool = pydantic.Field(None, env="MODELKIT_ASYNC_MODE")
    override_storage_prefix: Optional[str] = pydantic.Field(
        None, env="OVERRIDE_STORAGE_PREFIX"
    )
    enable_validation: bool = pydantic.Field(True, env="ENABLE_VALIDATION")
    tf_serving: TFServingSettings = pydantic.Field(
        default_factory=lambda: TFServingSettings()
    )
    cache: Optional[Union[RedisSettings, NativeCacheSettings]] = pydantic.Field(
        default_factory=lambda: cache_settings()
    )

    class Config:
        env_prefix = ""
