from bots.notifier_bot.bot import get_bot

import logging
log = logging.getLogger(__name__)


"""
send telegram notify id - telegram id of user, msg - message for notify
"""
async def send_notify(id: int, msg: str):
    bot = get_bot()
    if bot is None:
        raise RuntimeError("Bot is not initializated")
    await bot.send_message(id, msg)