from aiogram import Bot, Dispatcher

import bots.status_bot.handlers.common as common
import bots.status_bot.untils.notify_manager as notify_manager
import os

import logging

_log = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("STATUS_BOT_TOKEN")
BOT_ONLINE = os.getenv("STATUS_BOT_ONLINE") == "true"

dp = Dispatcher()
bot = Bot(BOT_TOKEN)

_log.info(f"token: {BOT_TOKEN}\nbot {'online' if BOT_ONLINE else 'offline'}")

async def start_bot():
    if not BOT_TOKEN:
        return
    
    notify_manager.init()

    dp.include_router(common.router)

    _log.info("status bot started")

    await dp.start_polling(bot)
    
def get_bot() -> Bot | None:
    return bot