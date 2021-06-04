import hashlib
import pickle
from typing import Any, Dict

import modelkit
from modelkit.utils.redis import connect_redis


class Cache:
    def get(self, key, default):
        pass

    def setdefault(self, key, value):
        pass


class RedisCache:
    def __init__(self, host, port):
        self.redis = connect_redis(host, port)
        self.cache_keys = {}

    def hash_key(self, model_key, item: Any, kwargs: Dict[str, Any]):
        cache_key = self.cache_keys.get(model_key)
        if not cache_key:
            self.cache_keys[model_key] = (model_key + modelkit.__version__).encode()
            cache_key = self.cache_keys[model_key]
        pickled = pickle.dumps((item, kwargs))  # nosec: only used to build a hash
        return hashlib.sha256(cache_key + pickled).digest()

    def get(self, k, d):
        r = self.redis.get(k)
        if r is None:
            return d
        return pickle.loads(r)

    def setdefault(self, k, d):
        self.redis.set(k, pickle.dumps(d))
