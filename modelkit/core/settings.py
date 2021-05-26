from typing import Optional

import pydantic


class ServiceSettings(pydantic.BaseSettings):
    enable_tf_serving: bool = pydantic.Field(False, env="ENABLE_TF_SERVING")
    tf_serving_mode: str = pydantic.Field("rest", env="TF_SERVING_MODE")
    tf_serving_host: str = pydantic.Field("localhost", env="TF_SERVING_HOST")
    tf_serving_port: int = pydantic.Field(None, env="TF_SERVING_PORT")
    tf_serving_timeout_s: int = pydantic.Field(60, env="TF_SERVING_TIMEOUT_S")

    lazy_loading: bool = pydantic.Field(False, env="LAZY_LOADING")
    async_mode: bool = pydantic.Field(None, env="modelkit_ASYNC_MODE")

    enable_redis_cache: bool = pydantic.Field(False, env="ENABLE_REDIS_CACHE")
    cache_host: str = pydantic.Field("localhost", env="CACHE_HOST")
    cache_port: int = pydantic.Field(6379, env="CACHE_PORT")

    override_storage_prefix: Optional[str] = pydantic.Field(
        None, env="OVERRIDE_STORAGE_PREFIX"
    )

    @pydantic.validator("tf_serving_port")
    @classmethod
    def default_serving_port(cls, v, values):
        if not v:
            v = 8500 if values["tf_serving_mode"] == "grpc" else 8501
        return v

    class Config:
        env_prefix = ""
