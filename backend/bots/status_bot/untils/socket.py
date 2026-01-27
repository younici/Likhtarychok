import asyncio
import websockets

import untils.states as states
import untils.redis_db as redis_un
import logging

_log = logging.getLogger(__name__)

_redis = None
_status: bool

async def handle_connection(websocket):
    _log.info("New WebSocket connection established")
    global _status

    try:
        if Light_Events.on and not _status:
            _log.info("Triggering light ON event")
            _status = True
            await Light_Events.on()            
            if _redis:
                await _redis.set("light_status", "1")
    except Exception as e:
        _log.error(f"Error executing Light_Events.on: {e}")
            
    try:
        await websocket.wait_closed()
    finally:
        if not states.closing:
            try:
                if Light_Events.off and _status:
                    _status = False
                    _log.info("Triggering light OFF event")
                    await Light_Events.off()                    
                    if _redis:
                        await _redis.set("light_status", "0")
            except Exception as e:
                _log.error(f"Error executing Light_Events.off: {e}")

def get_status() -> bool:
    return _status

async def main():
    await asyncio.sleep(0)

    _log.info("Starting WebSocket server on ws://0.0.0.0:8338")
    global _redis    
    global _status

    _redis = redis_un.get_redis_client()

    if _redis:
        status = await _redis.get("light_status")
        if status is not None:
            _status = bool(int(status))
        else:
            _status = False
    else:
        _status = False

    async with websockets.serve(
        handle_connection, 
        "0.0.0.0", 8338, 
        ping_interval=4,
        ping_timeout=6
    ):
        await asyncio.Future()

class Light_Events():
    on = None
    off = None