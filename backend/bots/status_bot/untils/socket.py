import asyncio
import websockets

import untils.states as states

import logging

_log = logging.getLogger(__name__)


_status: bool

async def handle_connection(websocket):
    _log.info("New WebSocket connection established")
    global _status

    if Light_Events.on:
        _log.info("Triggering light on event")
        await Light_Events.on()
    _status = True

    await websocket.wait_closed()

            
    try:
        await websocket.wait_closed()
    finally:
        if Light_Events.off and not states.closing:
            _log.info("Triggering light off event")
            await Light_Events.off()
        _status = False

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
        ping_interval=None
    ):
        await asyncio.Future()

class Light_Events():
    on = None
    off = None