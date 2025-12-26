import logging
import os

from aiogram import Bot, Dispatcher

from db.orm import utils as db
from help_bot.handlers import admin, common, tickets

HELP_BOT_TOKEN = os.getenv("HELP_BOT_TOKEN")

dp = Dispatcher()
bot: Bot | None = None


async def start_help_bot():
    """
    Launches help bot with separated handlers (common, admin, tickets).
    """
    global bot

    if not HELP_BOT_TOKEN:
        logging.info("HELP_BOT_TOKEN is not set; help bot will not start.")
        return

    bot = Bot(HELP_BOT_TOKEN)
    await db.ensure_primary_support_admin()

    dp.include_router(common.router)
    dp.include_router(admin.router)
    dp.include_router(tickets.router)

    await dp.start_polling(bot)


def get_help_bot() -> Bot | None:
    return bot
