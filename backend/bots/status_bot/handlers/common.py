from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandStart

import bots.status_bot.untils.socket as socket
import bots.status_bot.untils.subs as sub

router = Router()

START_MSG_ANSWER = """
Цей бот створений для сповіщення про відключення в реальному часі, на основі реальних відключень, але поки тільки під 3.1 чергу
Для перегляду списка команд скористайтесь /help
"""

HELP_MSG_ANSWER = """
Список команд:
/subscribe - Підписатись на сповіщення
/desubscribe - Відписатись від сповіщень
/status - Переглянути наявний статус світла
"""
@router.message(CommandStart())
async def start_cmd(msg: Message):
    await msg.answer(START_MSG_ANSWER)

@router.message(Command("help"))
async def help_cmd(msg: Message):
    await msg.answer(HELP_MSG_ANSWER)

@router.message(Command("subscribe"))
async def subscribe_cmd(msg: Message):
    if sub.add_sub(msg.from_user.id):
        await msg.answer("Підпииска додана")
    else:
        await msg.answer("Ви вже підписані")

@router.message(Command("desubscribe"))
async def desubscribe_cmd(msg: Message):
    if sub.remove_user(msg.from_user.id):
        await msg.answer("Ви видалили підписку")
    else:
        await msg.answer("Ви не підписані")

@router.message(Command("status"))
async def status_cmd(msg: Message):
    await msg.answer(f"Світло {'є' if socket.get_status() else 'немає'}")