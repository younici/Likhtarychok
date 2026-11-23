import asyncio
import json
import logging
import time

import untils.tools as tools
from untils.redis_db import get_redis_client

log = logging.getLogger(__name__)

REDIS_KEY = "cache_schedule"

# {"date": "dd.mm.yyyy" | None, "queues": {"11": [...48], ...}}
_cache: dict | None = None
_lock = asyncio.Lock()
_first_boot = True

# Min seconds between on-demand refreshes when the cached schedule is not for today.
ON_DEMAND_MIN_INTERVAL = 60
_last_on_demand = 0.0


def _is_fresh(data: dict | None) -> bool:
    """Cache is usable only if it belongs to today's schedule."""
    if not data or not data.get("queues"):
        return False
    date = data.get("date")
    return date is None or date == tools.today_str()


def _normalize(data: dict) -> dict:
    return {
        "date": data.get("date"),
        "queues": {str(k): list(v) for k, v in (data.get("queues") or {}).items()},
    }


async def _save_cache_to_redis(data: dict):
    redis = get_redis_client()
    if not redis or not data:
        return
    try:
        await redis.set(REDIS_KEY, json.dumps(data))
        log.info("Schedule cache saved to Redis")
    except Exception as e:
        log.error(f"Redis save error: {e}")


async def _get_cache_from_redis() -> dict | None:
    redis = get_redis_client()
    if not redis:
        return None
    try:
        raw = await redis.get(REDIS_KEY)
        if raw:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
    except Exception as e:
        log.error(f"Redis load error: {e}")
    return None


async def cache_loop():
    """Downloads the ZTOE page once and refreshes the schedule for all queues."""
    global _cache, _first_boot

    if _lock.locked():
        # Another refresh is in progress: wait for it instead of returning stale/empty data.
        async with _lock:
            return

    async with _lock:
        if _first_boot:
            _first_boot = False
            data = await _get_cache_from_redis()
            if _is_fresh(data):
                _cache = _normalize(data)
                log.info("Schedule cache loaded from Redis")

        try:
            schedule = await tools.get_schedule()
        except Exception as e:
            log.error(f"Error in cache_loop: {e!r}")
            schedule = None

        if not schedule:
            log.warning("Schedule fetch/parse failed, keeping previous cache")
            return

        new_cache = _normalize(schedule)

        # If some queues failed to parse, keep their previous values for the same day.
        if _cache and _cache.get("date") == new_cache["date"]:
            for code, value in _cache["queues"].items():
                new_cache["queues"].setdefault(code, value)

        _cache = new_cache
        log.info(f"Schedule cache updated: date={_cache['date']}, queues={len(_cache['queues'])}")
        await _save_cache_to_redis(_cache)


_refresh_task: asyncio.Task | None = None
REQUEST_WAIT_TIMEOUT = 8


async def _refresh_if_stale():
    """Never blocks an API request for long: refresh runs as a background task."""
    global _last_on_demand, _refresh_task
    if _is_fresh(_cache):
        return

    if _refresh_task is None or _refresh_task.done():
        now = time.monotonic()
        if now - _last_on_demand < ON_DEMAND_MIN_INTERVAL:
            return
        _last_on_demand = now
        _refresh_task = asyncio.create_task(cache_loop())

    try:
        await asyncio.wait_for(asyncio.shield(_refresh_task), REQUEST_WAIT_TIMEOUT)
    except asyncio.TimeoutError:
        log.warning("Schedule refresh is slow, answering with current cache")
    except Exception as e:
        log.error(f"Schedule refresh failed: {e!r}")


async def get_cache(queue_code: int) -> list[int] | None:
    """Returns 48 slot statuses (1 = outage) for queue code like 11, 12 ... 62."""
    await _refresh_if_stale()

    if not _cache:
        return None

    if not _is_fresh(_cache):
        log.warning(f"Serving schedule for {_cache.get('date')}, today is {tools.today_str()}")

    status = _cache["queues"].get(str(queue_code))
    if status is None:
        log.error(f"Queue {queue_code} not found in cache")
    return status


async def get_all_cache() -> dict:
    await _refresh_if_stale()
    return dict((_cache or {}).get("queues") or {})
