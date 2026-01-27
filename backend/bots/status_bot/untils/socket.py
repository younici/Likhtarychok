import untils.states as states
import untils.redis_db as redis_un

import time, redis, asyncio, websockets, logging

_log = logging.getLogger(__name__)

_redis: redis.Redis | None = None
_status = False
_start: float = 0

_last_con_time: float = 0
_last_con_duration: float = 0
_last_on_trigger: float = 0
_last_off_trigger: float = 0
DEBOUNCE_ON_SEC = 30
DEBOUNCE_OFF_SEC = 30
async def handle_connection(websocket):
    _log.info("New WebSocket connection established")

    global _status, _start
    global _last_con_duration, _last_con_time
    global _last_on_trigger, _last_off_trigger

    now = time.time()

    if _start == 0:
        _start = now

    # ===== DEBOUNCE ON =====
    try:
        if Light_Events.on and not _status:
            if now - _last_on_trigger >= DEBOUNCE_ON_SEC:
                _log.info("Triggering light ON event")
                _last_on_trigger = now
                _status = True
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

            # ===== DEBOUNCE OFF =====
            try:
                if Light_Events.off and _status:
                    if now - _last_off_trigger >= DEBOUNCE_OFF_SEC:
                        _last_con_duration = get_connection_time()
                        _last_con_time = now

                        _log.info("Triggering light OFF event")
                        _last_off_trigger = now

                        await Light_Events.off()

                        _start = 0
                        _status = False
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

async def save_all():
    global _start
    if _redis:
        await _redis.set("socket_start_time", str(_start))
        await _redis.set("light_status", str(int(_status)))
        await _redis.set("last_connection_time", str(int(_last_con_time)))
        await _redis.set("last_connection_duration", str(int(_last_con_duration)))

async def load_all():
    global _redis
    global _status
    global _start
    global _last_con_time
    global _last_con_duration

    _redis = redis_un.get_redis_client()

    if _redis:
        status = await _redis.get("light_status")
        if status is not None:
            _status = bool(int(status))
        else:
            _status = False
        start = await _redis.get("socket_start_time")
        if start is not None:
            _start = float(start)
        last_time = await _redis.get("last_connection_time")
        if last_time is not None:
            _last_con_time = float(last_time)
        else:
            _last_con_time = 0
        last_duration = await _redis.get("last_connection_duration")
        if last_duration is not None:
            _last_con_duration = float(last_duration)
        else:
            _last_con_duration = 0

async def main():
    await asyncio.sleep(0)
    _log.info("Starting WebSocket server on ws://0.0.0.0:8338")

    await load_all()

    async with websockets.serve(
        handle_connection, 
        "0.0.0.0", 8338, 
        ping_interval=5,
        ping_timeout=20
    ):
        await asyncio.Future()

class Light_Events():
    on = None
    off = None