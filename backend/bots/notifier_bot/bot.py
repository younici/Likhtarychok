from aiogram import Bot, Dispatcher
import os

import bots.notifier_bot.handlers.queue as queue
import bots.notifier_bot.handlers.start as start

BOT_TOKEN = os.getenv("NOTIFY_BOT_TOKEN")
BOT_ONLINE = os.getenv("NOTIFY_BOT_ONLINE") == "true"

dp = Dispatcher()
bot = Bot(BOT_TOKEN)

async def start_bot():
    if not BOT_ONLINE or not BOT_TOKEN:
        return
    
    dp.include_routers(queue.router, start.router)
    await dp.start_polling(bot)

def get_bot() -> Bot | None:
    return bot