import logging
import os

from aiogram import Bot, Dispatcher

from db.orm import utils as db
from bots.help_bot.handlers import admin, common, tickets

HELP_BOT_TOKEN = os.getenv("HELP_BOT_TOKEN")
BOT_ONLINE = os.getenv("HELP_BOT_ONLINE") == "true"

dp = Dispatcher()
bot: Bot | None = None


async def start_bot():
    if not BOT_ONLINE or not HELP_BOT_TOKEN:
        return
    
    global bot
    bot = Bot(HELP_BOT_TOKEN)
    
    await db.ensure_primary_support_admin()
    dp.include_routers(common.router, admin.router, tickets.router)

    await dp.start_polling(bot)


def get_help_bot() -> Bot | None:
    return bot
