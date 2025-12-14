from untils.variebles import QUEUE_LABELS
import untils.tools as tools

import logging

log = logging.getLogger(__name__)

_cache_queue = []

_all_index = []
_all_bias = []

for index in QUEUE_LABELS:
    _all_index.append(tools.queue_to_index(index))
for index in _all_index:
    _all_bias.append(tools.bias_from_index(index))

async def cache_loop():
    new_cache = []
    for queue, bias in zip(_all_index, _all_bias):
        new_cache.append(await tools.get_status(queue, bias))
        
    global _cache_queue
    _cache_queue = new_cache
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
