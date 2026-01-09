import asyncio
from datetime import datetime, timedelta

_mongo_cache = {}
CACHE_TTL = timedelta(minutes=5)
_cache_lock = asyncio.Lock()


async def cached_mongo_call(collection, method: str, filter: dict):
    """
    Generic cached version for MongoDB operations like find_one and count_documents.
    """
    key = (collection.name, method, frozenset(filter.items()))

    async with _cache_lock:
        cached = _mongo_cache.get(key)
        if cached and cached[1] > datetime.utcnow():
            return cached[0]

    # call the actual collection method
    func = getattr(collection, method)
    result = await func(filter)

    # store in cache
    async with _cache_lock:
        _mongo_cache[key] = (result, datetime.utcnow() + CACHE_TTL)

    return result


async def invalidate_cache(filter: dict = None, collection=None, method: str = None):
    """
    Invalidate cache entries.
    - If filter + method + collection are given → invalidate specific entry.
    - If only collection is given → invalidate all cache for this collection.
    - If nothing given → invalidate everything.
    """
    async with _cache_lock:
        keys_to_remove = []
        for key in _mongo_cache:
            coll_name, key_method, key_filter = key
            if collection and coll_name != collection.name:
                continue
            if method and key_method != method:
                continue
            if filter and frozenset(filter.items()) != key_filter:
                continue
            keys_to_remove.append(key)
        for key in keys_to_remove:
            _mongo_cache.pop(key, None)


# ------------------------------
# Automatic invalidation helpers
# ------------------------------


async def insert_one(collection, document):
    result = await collection.insert_one(document)
    await invalidate_cache(collection=collection)  # invalidate all for collection
    return result


async def update_one(collection, filter: dict, update: dict):
    result = await collection.update_one(filter, update, upsert=True)
    await invalidate_cache(filter, collection)  # invalidate cache for this filter
    return result


async def delete_one(collection, filter: dict):
    result = await collection.delete_one(filter)
    await invalidate_cache(filter, collection)  # invalidate cache for this filter
    return result
