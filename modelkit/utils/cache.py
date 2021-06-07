import hashlib
import pickle
from typing import Any, Dict, Generic, Optional

import pydantic

import modelkit
from modelkit.core.types import ItemType
from modelkit.utils.redis import connect_redis


class CacheItem(Generic[ItemType]):
    def __init__(
        self,
        item: Optional[ItemType] = None,
        cache_key: bytes = None,
        cache_value=None,
        missing: bool = True,
    ):
        self.item = item
        self.cache_key = cache_key
        self.cache_value = cache_value
        self.missing = missing


class RedisCache:
    def __init__(self, host, port):
        self.redis = connect_redis(host, port)
        self.cache_keys = {}

    def hash_key(self, model_key: str, item: Any, kwargs: Dict[str, Any]):
        cache_key = self.cache_keys.get(model_key)
        if not cache_key:
            self.cache_keys[model_key] = (model_key + modelkit.__version__).encode()
            cache_key = self.cache_keys[model_key]
        pickled = pickle.dumps((item, kwargs))  # nosec: only used to build a hash
        return hashlib.sha256(cache_key + pickled).digest()

    def get(self, model_key: str, item: Any, kwargs: Dict[str, Any]):
        cache_key = self.hash_key(model_key, item, kwargs)
        r = self.redis.get(cache_key)
        if r is None:
            return CacheItem(cache_key=cache_key, item=item, missing=True)
        return CacheItem(
            cache_key=cache_key, cache_value=pickle.loads(r), missing=False
        )

    def set(self, k: bytes, d: Any):
        if isinstance(d, pydantic.BaseModel):
            self.redis.set(k, pickle.dumps(d.dict()))
        else:
            self.redis.set(k, pickle.dumps(d))
