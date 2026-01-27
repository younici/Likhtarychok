import asyncio
import websockets

import untils.states as states

import logging

_log = logging.getLogger(__name__)


_status: bool

async def handle_connection(websocket):
    _log.info("New WebSocket connection established")
    global _status

    try:
        if Light_Events.on:
            _log.info("Triggering light ON event")
            await Light_Events.on()
    except Exception as e:
        _log.error(f"Error executing Light_Events.on: {e}")

    await websocket.wait_closed()

            
    try:
        await websocket.wait_closed()
    finally:
        if not states.closing:
            try:
                if Light_Events.off:
                    _log.info("Triggering light OFF event")
                    await Light_Events.off()
            except Exception as e:
                _log.error(f"Error executing Light_Events.off: {e}")

def get_status() -> bool:
    return _status

async def main():
    await asyncio.sleep(0)

    _log.info("Starting WebSocket server on ws://0.0.0.0:8338")
    
    global _status
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