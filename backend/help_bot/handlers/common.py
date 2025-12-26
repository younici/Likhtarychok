from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

import db.orm.utils as db

router = Router()

START_TEXT = (
    "Привіт! Це бот підтримки Likhtarychok.\n"
    "Опишіть питання одним повідомленням — створимо заявку та передамо адміністраторам. "
    "Відповідь отримаєте тут."
)

HELP_TEXT = (
    "/start — коротко про бота\n"
    "/help — список команд\n"
)

ADMIN_HELP_TEXT = (
    "/admins — показати адміністраторів\n"
    "/add_admin <tg_id> — додати адміністратора\n"
    "/del_admin <tg_id> - видалити адміна с дб\n"
    "/reply <id> <текст> — відповісти на заявку\n"
    "/del_ticket <id> — видалити заявку\n"
    "/ban <user_id> <хвилини> <причина> — тимчасовий бан користувача\n"
    "/unban <user_id> — зняти бан"
)


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(START_TEXT)


@router.message(Command("help"))
async def cmd_help(message: Message):
    answer_text = HELP_TEXT
    if await db.is_support_admin(message.from_user.id):
        answer_text += ADMIN_HELP_TEXT
    await message.answer(answer_text)
