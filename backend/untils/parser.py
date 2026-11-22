import untils.cache as cache
import untils.tools as tools

import os

CAN_CACHE = os.getenv("CAN_CACHE", "true").lower() == "true"

import logging

log = logging.getLogger(__name__)

log.info(f"cache status: {CAN_CACHE}")


async def parse(queue: int):
    """
    Returns a list of 48 half-hour slots for queue code (11, 12 ... 62):
    1 - outage, 0 - power is on. None if data is unavailable.
    """
    queue = int(queue)

    if CAN_CACHE:
        return await cache.get_cache(queue)

    schedule = await tools.get_schedule()
    if not schedule:
        return None
    return schedule["queues"].get(queue)
