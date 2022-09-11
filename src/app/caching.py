import shelve 
import logging
from functools import wraps
import asyncio
from typing import Any, Dict
from prometheus_client import Counter, Gauge, Histogram
import cachetools
import datetime
import common
from common.utils import Repository
import asyncio
# from common.utils import Repository

logger = logging.getLogger(__name__)



class MonitoredTTLCache(cachetools.TTLCache):
    cache_hits: Counter
    cache_misses: Counter
    cache_evictions: Counter
    cache_items: Counter
    cache_name: str
    def __init__(self, cache_name: str, *args, **kwargs) -> None:
        self.cache_name = cache_name
        self.cache_hits = Counter(f"{self.cache_name}_cache_hits", "Number of hits in cache")
        self.cache_misses = Counter(f"{self.cache_name}_cache_misses", "Number of misses in cache")
        self.cache_evictions = Counter(f"{self.cache_name}_cache_evictions", "Number of evictions in cache")
        self.cache_items = Gauge(f"{self.cache_name}_cache_items", "Number of items in cache")
        
        
        return super().__init__(maxsize=kwargs.get("maxsize", 1000), ttl=kwargs.get("ttl", 3600))
    
    def __getitem__(self, key):
        try:
            res = super().__getitem__(key)
            self.cache_hits.inc()
            return res
        except Exception as e:
            self.cache_misses.inc()
            raise e
    
    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.cache_items.inc()
        
    def popitem(self):
        res = super().popitem()
        self.cache_evictions.inc()
        self.cache_items.set(len(list(self.keys())))
        return res
    
    def __delitem__(self, key):
        super().__delitem__(key)
        self.cache_items.set(len(list(self.keys())))
        # self.cache_evictions.inc()

class CachedMeetingsById(MonitoredTTLCache):
    repo: Repository
    def __init__(self, *args):
        self.repo = Repository("meetings")
        return super().__init__(*args)
    def __missing__(self, key:str):
        # returns an awaitable object
        self.cache_misses.labels(name="meetings").inc()
        res_future = asyncio.create_task(self.repo.get({"_id": key}))
        self[key] = res_future
        return res_future



def caches(cache: cachetools.Cache, key):
    def wrapper(fn):
        @wraps(fn)
        async def wrapped(*args, **kwargs):
            try:
                cached = cache[kwargs[key]]
                return cached
            except Exception as e:
                pass
            res = await fn(*args, **kwargs)
            cache[kwargs[key]] = res
            return res
        return wrapped
    return wrapper

def cache_deletes(cache: cachetools.Cache, key):
    def wrapper(fn):
        @wraps(fn)
        async def wrapped(*args, **kwargs):
            res = await fn(*args, **args)
            del cache[kwargs[key]]
            return res
        return wrapped
    return wrapper

# def caches_for_seconds(cache: cachetools.Cache, key, for_seconds: int):
#     def wrapper(fn):
#         @wraps(fn)
#         async def wrapped(*args, **kwargs):
#             cached = cache[kwargs[key]]
#             #if it's present then return
#             if cached:
#                 return cached
#             # else execute function, get result and store by its id
#             CACHE_MISSES.labels(name="meetings").inc()
#             res = await fn(*args, **kwargs)
#             cache[kwargs[key]] = res
            
#             loop = asyncio.get_event_loop()
#             loop.call_later(for_seconds, delete_by_key, for_seconds)
#             return res
#         return wrapped
#     return wrapper