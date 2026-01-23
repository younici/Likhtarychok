from untils.variebles import QUEUE_LABELS
import untils.tools as tools
import asyncio
import json
from untils.redis_db import get_redis_client
import logging

log = logging.getLogger(__name__)

_cache_queue = []

_all_index = []
_all_bias = []

first_boot = True

for queue_label in QUEUE_LABELS:
    idx = tools.queue_to_index(queue_label)
    _all_index.append(idx)
    _all_bias.append(tools.bias_from_index(idx))

getting_status = False

async def _save_cache_to_redis(data_to_save: list):
    redis = get_redis_client()
    if not redis:
        return
    if data_to_save:
        try:
            await redis.set("cache_queue", json.dumps(data_to_save))
            log.info("Cache saved to Redis")
        except Exception as e:
            log.error(f"Redis save error: {e}")

async def _get_cahce_from_redis() -> list | None:
    redis = get_redis_client()
    if not redis:
        return None
    try:
        data = await redis.get("cache_queue")
        if data:
            return json.loads(data)
    except Exception as e:
        log.error(f"Redis load error: {e}")
    return None

async def cache_loop():
    global getting_status
    global _cache_queue
    global first_boot
    
    if getting_status:
        return

    getting_status = True
    
    if first_boot:
        first_boot = False
        data = await _get_cahce_from_redis()
        if data:
            _cache_queue = data
            log.info("Cache loaded from redis")

    new_cache = []
    
    try:
        for queue, bias in zip(_all_index, _all_bias):
            log.info(f"getting cache for queue_idx: {queue} (bias: {bias})")
            status = await tools.get_status(queue, bias)
            
            if status is None:
                log.warning(f"Got None for queue index {queue}")
                new_cache.append("") 
            else:
                new_cache.append(status)
                
            await asyncio.sleep(1)
        if new_cache and len(new_cache) == len(_all_index):
            _cache_queue = new_cache
            await _save_cache_to_redis(_cache_queue)
        else:
            log.warning(f"Cache incomplete. Got {len(new_cache)}, expected {len(_all_index)}")

    except Exception as e:
        log.error(f"Error in cache_loop: {e}")
    finally:
        getting_status = False

async def get_cache(queue):
    if not _cache_queue:
        await cache_loop()
    list_idx = queue - 1
    
    if 0 <= list_idx < len(_cache_queue):
        return _cache_queue[list_idx]
    
    log.error(f"Queue index {queue} out of range (cache len: {len(_cache_queue)})")
    return None

async def get_all_cache():
    if not _cache_queue:
        await cache_loop()
    return _cache_queue