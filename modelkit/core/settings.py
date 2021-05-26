from typing import Optional

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


class RedisSettings(pydantic.BaseSettings):
    enable: bool = pydantic.Field(False, env="ENABLE_REDIS_CACHE")
    host: str = pydantic.Field("localhost", env="CACHE_HOST")
    port: int = pydantic.Field(6379, env="CACHE_PORT")


class LibrarySettings(pydantic.BaseSettings):
    lazy_loading: bool = pydantic.Field(False, env="LAZY_LOADING")
    async_mode: bool = pydantic.Field(None, env="MODELKIT_ASYNC_MODE")
    override_storage_prefix: Optional[str] = pydantic.Field(
        None, env="OVERRIDE_STORAGE_PREFIX"
    )

    tf_serving: TFServingSettings = pydantic.Field(
        default_factory=lambda: TFServingSettings()
    )
    redis: RedisSettings = pydantic.Field(default_factory=lambda: RedisSettings())

    class Config:
        env_prefix = ""
