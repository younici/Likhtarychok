import bots.status_bot.untils.socket as socket

import time

_LIGHT_ON_MSG = """Світло ввімкнули
"""
_LIGHT_OFF_MSG = """Світло вимкнули
""" 
import logging
_log = logging.getLogger(__name__)

_enabled = True

def init():
    _log.info("Initializing light event handlers")
    socket.Light_Events.on = light_on
    socket.Light_Events.off = light_off

def set_enabled(enabled: bool):
    global _enabled
    _enabled = enabled

def get_enabled() -> bool:
    return _enabled

async def light_on():
    if not _enabled:
        return
    
    import bots.status_bot.untils.notify as notifier
    _log.info("notified light on")
    msg = _LIGHT_ON_MSG + f", його не було {int(time.time() - socket.get_last_con_time())} секунд"
    await notifier.notify_all(msg)

async def light_off():
    if not _enabled:
        return

    import bots.status_bot.untils.notify as notifier
    _log.info("notified light off")
    msg = _LIGHT_OFF_MSG + f", світло було {int(socket.get_last_con_duration())} секунд"
    await notifier.notify_all(msg)
    