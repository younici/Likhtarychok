from functools import wraps
from aiogram.types import Message

import os

_admins = os.getenv("BOT_ADMINS", "").split(",")

def admin_only(func):
    @wraps(func)
    async def wrapper(msg: Message, *args, **kwargs):
        admin_ids = [int(admin_id) for admin_id in _admins if admin_id.isdigit()]
        if msg.from_user.id not in admin_ids:
            await msg.answer("You do not have permission to use this command.")
            return
        return await func(msg, *args, **kwargs)
    return wrapper