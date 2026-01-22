import functools
import hashlib
import json
from datetime import timedelta
from typing import Any, Callable, Dict, List, Optional, Union
from cachetools import TTLCache

class CacheManager:
    def __init__(self, default_ttl: int = 300, maxsize: int = 1000):
        self._caches: Dict[str, TTLCache] = {}
        self._tag_to_keys: Dict[str, set] = {}
        self._default_ttl = default_ttl
        self._maxsize = maxsize

    def _get_cache(self, ttl: int) -> TTLCache:
        cache_key = f"ttl_{ttl}"
        if cache_key not in self._caches:
            self._caches[cache_key] = TTLCache(maxsize=self._maxsize, ttl=ttl)
        return self._caches[cache_key]

    def _generate_key(self, func: Callable, args: tuple, kwargs: dict) -> str:
        # Create a stable key from function name and arguments
        # Handle non-serializable objects (like MyResponse or other complex types)
        # We'll use a simplified version for now
        arg_str = str(args) + str(sorted(kwargs.items()))
        hash_val = hashlib.md5(arg_str.encode()).hexdigest()
        return f"{func.__name__}:{hash_val}"

    def cached(self, ttl: Optional[int] = None, tags: Optional[List[str]] = None):
        ttl = ttl or self._default_ttl
        tags = tags or []

        def decorator(func: Callable):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                cache = self._get_cache(ttl)
                key = self._generate_key(func, args, kwargs)

                if key in cache:
                    # print(f"Cache hit for {key}")
                    return cache[key]

                # print(f"Cache miss for {key}")
                result = await func(*args, **kwargs)
                
                # Only cache successful results (assuming MyResponse object)
                # If it's not a MyResponse object, we might need a more generic check
                cache[key] = result
                
                # Track keys by tags for invalidation
                for tag in tags:
                    if tag not in self._tag_to_keys:
                        self._tag_to_keys[tag] = set()
                    self._tag_to_keys[tag].add((ttl, key))
                
                return result
            return wrapper
        return decorator

    def invalidate(self, tags: Union[str, List[str]]):
        if isinstance(tags, str):
            tags = [tags]
        
        for tag in tags:
            if tag in self._tag_to_keys:
                for ttl, key in self._tag_to_keys[tag]:
                    cache = self._get_cache(ttl)
                    if key in cache:
                        del cache[key]
                del self._tag_to_keys[tag]
                # print(f"Invalidated cache for tag: {tag}")

cache_manager = CacheManager()
