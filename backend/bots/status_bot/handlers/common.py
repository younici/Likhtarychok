from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandStart

import bots.status_bot.untils.socket as socket
import bots.status_bot.untils.subs as sub
from bots.status_bot.untils.decorators import admin_only

router = Router()

START_MSG_ANSWER = (
    "Цей бот створений для сповіщення про відключення світла в реальному часі.\n"
    "Наразі працює для 3.1 черги.\n\n"
    "Для перегляду команд використовуйте /help"
)

HELP_MSG_ANSWER = (
    "Список команд:\n"
    "/subscribe — Підписатись на сповіщення\n"
    "/desubscribe — Відписатись від сповіщень\n"
    "/status — Поточний статус світла\n"
    "/time — Тривалість поточного стану\n"
    "/help — Показати це повідомлення\n"
    "/start — Привітальне повідомлення"
)


@router.message(CommandStart())
async def start_cmd(msg: Message):
    await msg.answer(START_MSG_ANSWER)

@router.message(Command("help"))
async def help_cmd(msg: Message):
    await msg.answer(HELP_MSG_ANSWER)

@router.message(Command("subscribe"))
async def subscribe_cmd(msg: Message):
    if sub.add_sub(msg.from_user.id):
        await msg.answer("Підписка додана")
    else:
        await msg.answer("Ви вже підписані")

@router.message(Command("desubscribe"))
async def desubscribe_cmd(msg: Message):
    if sub.remove_user(msg.from_user.id):
        await msg.answer("Ви відписались від сповіщень")
    else:
        await msg.answer("Ви не підписані")

@router.message(Command("status"))
async def status_cmd(msg: Message):
    if socket.get_status():
        await msg.answer("Світло є")
        return

    last_time = socket.get_last_con_time()
    if last_time == 0:
        await msg.answer("Світло відсутнє, востаннє світло було невідомо коли")
    else:
        await msg.answer(
            f"Світло відсутнє, востаннє світло було {int(last_time)} секунд тому"
        )


@router.message(Command("time"))
async def time_cmd(msg: Message):
    if socket.get_status():
        conn_time = socket.get_connection_time()
        await msg.answer(f"Світло є вже {int(conn_time)} секунд")
        return

    last_duration = socket.get_last_con_duration()
    if last_duration == 0:
        await msg.answer("Світло відсутнє. Дані про попередній стан відсутні")
    else:
        await msg.answer(
            f"Світло відсутнє. Востаннє світло було {int(last_duration)} секунд"
        )


@router.message(Command("notify_switch"))
@admin_only
async def notify_switch_cmd(msg: Message):
    import bots.status_bot.untils.notify_manager as notify_manager

    new_state = not notify_manager.get_enabled()
    notify_manager.set_enabled(new_state)

    await msg.answer(
        f"Сповіщення про зміну стану світла "
        f"{'увімкнені' if new_state else 'вимкнені'}"
    )
