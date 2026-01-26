import bots.status_bot.untils.socket as socket

_LIGHT_ON_MSG = """Світло ввімкнули
"""
_LIGHT_OFF_MSG = """Світло вимкнули
""" 
import logging
_log = logging.getLogger(__name__)

def init():
    _log.info("Initializing light event handlers")
    socket.Light_Events.on = light_on
    socket.Light_Events.off = light_off

async def light_on():
    import bots.status_bot.untils.notify as notifier
    _log.info("notified light on")
    await notifier.notify_all(_LIGHT_ON_MSG)

async def light_off():
    import bots.status_bot.untils.notify as notifier
    _log.info("notified light off")
    await notifier.notify_all(_LIGHT_OFF_MSG)
    