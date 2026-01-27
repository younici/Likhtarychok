from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandStart

import bots.status_bot.untils.socket as socket
import bots.status_bot.untils.subs as sub
from bots.status_bot.untils.decorators import admin_only

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
/time - Переглянути час тривалість наявності світла
/help - Показати це повідомлення
/start - Показати привітальне повідомлення
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
    status = socket.get_status()
    if status:
        await msg.answer("Світло є")
    else:
        last_con_time = socket.get_last_con_time()
        await msg.answer("Світло відсутнє, востаннє світло було " + (f"{int(last_con_time)} секунд тому" if last_con_time != 0 else "невідомо коли"))

@router.message(Command("time"))
async def time_cmd(msg: Message):
    conn_time = socket.get_connection_time()
    if conn_time == 0:
        last_con_duration = socket.get_last_con_duration()
        await msg.answer(f"Світло відсутнє. Востаннє світло було {int(last_con_duration)} секунд")
    else:
        await msg.answer(f"Світло є вже {int(conn_time)} секунд")

@router.message(Command("notify_switch"))
@admin_only
async def notify_switch_cmd(msg: Message):
    import bots.status_bot.untils.notify_manager as notify_manager

    current_state = notify_manager.get_enabled()
    new_state = not current_state
    notify_manager.set_enabled(new_state)

    await msg.answer(f"Сповіщення про зміну стану світла тепер {'увімкнені' if new_state else 'вимкнені'}")