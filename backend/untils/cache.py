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

_redis = get_redis_client()

first_boot = True

for index in QUEUE_LABELS:
    _all_index.append(tools.queue_to_index(index))
for index in _all_index:
    _all_bias.append(tools.bias_from_index(index))

async def cache_loop():
    if first_boot:
        await _get_cahce_from_redis()
        first_boot = False
        return
    
    new_cache = []
    for queue, bias in zip(_all_index, _all_bias):
        new_cache.append(await tools.get_status(queue, bias))
        await asyncio.sleep(5)
    
    global _cache_queue
    if new_cache and (len(new_cache) == (len(_all_index) + len(_all_bias))):
        _cache_queue = new_cache
        await _save_cache_to_redis(_cache_queue)
    else:
        await asyncio.sleep(30)
        await cache_loop()
        return

    log.debug(f"\n\tall_index: {_all_index}\n\tall_bias: {_all_bias}\n\tcache: {_cache_queue}\n\t")

async def get_cache(queue):
    if not _cache_queue:
        await cache_loop()
    
    log.debug(f"{_cache_queue}")

    return _cache_queue[queue-1]

async def get_all_cache():
    if not _cache_queue:
        await cache_loop()
    
    return _cache_queue

async def _save_cache_to_redis(_cache_queue: list[str]):
    if not _redis and _cache_queue:
        return
    await _redis.set("cache_queue", json.dumps(_cache_queue))


async def _get_cahce_from_redis():
    if not _redis:
        return
    data = await _redis.get("cache_queue")
    if data:
        global _cache_queue
        _cache_queue = json.loads(data)
