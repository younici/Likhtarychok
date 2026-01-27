import untils.states as states

import time
import redis
import asyncio
import websockets
import logging

_log = logging.getLogger(__name__)

DEBOUNCE_ON_SEC = 30
DEBOUNCE_OFF_SEC = 30

_status: bool = False
_start: float = 0    

_last_con_time: float = 0 
_last_con_duration: float = 0 

_last_on_trigger: float = 0
_last_off_trigger: float = 0

_light_off_since: float = 0  

async def handle_connection(websocket):
    _log.info("New WebSocket connection established")

    global _status, _start
    global _last_con_duration, _last_con_time
    global _last_on_trigger, _last_off_trigger
    global _light_off_since

    now = time.time()

    try:
        if Light_Events.on and not _status:
            if now - _last_on_trigger >= DEBOUNCE_ON_SEC:
                _log.info("Triggering light ON event")
                _last_on_trigger = now

                _status = True
                _start = now

                await Light_Events.on()
            else:
                _log.debug("ON ignored (debounce)")
    except Exception as e:
        _log.error(f"Error executing Light_Events.on: {e}")

    try:
        await websocket.wait_closed()

    finally:
        if not states.closing:
            now = time.time()

            try:
                if Light_Events.off and _status:
                    if now - _last_off_trigger >= DEBOUNCE_OFF_SEC:
                        _log.info("Triggering light OFF event")
                        _last_off_trigger = now

                        _last_con_duration = get_connection_time()
                        _last_con_time = now
                        _light_off_since = now

                        await Light_Events.off()

                        _status = False
                        _start = 0
                    else:
                        _log.debug("OFF ignored (debounce)")
            except Exception as e:
                _log.error(f"Error executing Light_Events.off: {e}")


def get_status() -> bool:
    return _status

def get_connection_time() -> float:
    if _start == 0:
        return 0.0
    return time.time() - _start

def get_last_con_duration() -> float:
    return _last_con_duration

def get_last_con_time() -> float:
    return _last_con_time

def get_light_off_duration() -> int:
    if _light_off_since == 0:
        return 0
    return int(time.time() - _light_off_since)

async def save_all(redis_client: redis.Redis | None = None):
    if not redis_client:
        return

    await redis_client.set("light_status", int(_status))
    await redis_client.set("socket_start_time", _start)
    await redis_client.set("last_connection_time", _last_con_time)
    await redis_client.set("last_connection_duration", _last_con_duration)
    await redis_client.set("light_off_since", _light_off_since)

async def load_all(redis_client: redis.Redis | None = None):
    global _status, _start
    global _last_con_time, _last_con_duration
    global _light_off_since

    if not redis_client:
        return

    def _get_float(key: str) -> float:
        val = redis_client.get(key)
        return float(val) if val else 0

    def _get_bool(key: str) -> bool:
        val = redis_client.get(key)
        return bool(int(val)) if val else False

    _status = await _get_bool("light_status")
    _start = await _get_float("socket_start_time")
    _last_con_time = await _get_float("last_connection_time")
    _last_con_duration = await _get_float("last_connection_duration")
    _light_off_since = await _get_float("light_off_since")


async def main(redis_client: redis.Redis | None = None):
    await asyncio.sleep(0)
    _log.info("Starting WebSocket server on ws://0.0.0.0:8338")

    await load_all(redis_client)

    async with websockets.serve(
        handle_connection,
        "0.0.0.0",
        8338,
        ping_interval=5,
        ping_timeout=20
    ):
        await asyncio.Future()
class Light_Events:
    on = None
    off = None