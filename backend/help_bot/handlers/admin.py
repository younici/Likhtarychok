import logging
from datetime import datetime, timedelta
from os import getenv

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

import db.orm.utils as db

router = Router()
BASE_ADMIN_ID = int(getenv("HELP_BASE_ADMIN_ID", "0") or 0)


def _require_admin(func):
  async def wrapper(message: Message, *args, **kwargs):
    if not await db.is_support_admin(message.from_user.id):
      await message.answer("Команда доступна тільки адміністраторам.")
      return
    return await func(message, *args, **kwargs)

  return wrapper


@router.message(Command("admins"))
@_require_admin
async def cmd_admins(message: Message, **_):
  admins = await db.list_support_admin_ids()
  if not admins:
    await message.answer("Адміністраторів поки немає.")
    return
  lines = [f"- {admin_id}" + (" (базовий)" if admin_id == BASE_ADMIN_ID and BASE_ADMIN_ID else "") for admin_id in admins]
  await message.answer("Адміністратори:\n" + "\n".join(lines))


@router.message(Command("add_admin"))
@_require_admin
async def cmd_add_admin(message: Message, **_):
  parts = message.text.split(maxsplit=1)
  if len(parts) < 2:
    await message.answer("Використання: /add_admin <tg_id>")
    return

  try:
    new_admin = int(parts[1])
  except ValueError:
    await message.answer("tg_id має бути числом.")
    return

  added = await db.ensure_support_admin(new_admin, is_primary=False)
  if added:
    await message.answer(f"Адміністратора {new_admin} додано.")
  else:
    await message.answer("Не вдалося додати адміністратора.")


@router.message(Command("del_admin"))
@_require_admin
async def cmd_del_admin(msg: Message):
  parts = msg.text.split(maxsplit=1)
  if len(parts) < 2:
    await msg.answer("Використання: /del_admin <tg_id>")
    return

  try:
    del_admin = int(parts[1])
  except ValueError:
    await msg.answer("tg_id має бути числом.")
    return

  if await db.remove_support_admin(del_admin):
    await msg.answer(f"Адмін з айді {del_admin} успішно видалений")
  else:
    await msg.answer(f"Адміна з айді {del_admin} немає в дб")


@router.message(Command("reply"))
@_require_admin
async def cmd_reply(message: Message, **_):
  parts = message.text.split(maxsplit=2)
  if len(parts) < 3:
    await message.answer("Використання: /reply <id> <текст відповіді>")
    return

  try:
    ticket_id = int(parts[1])
  except ValueError:
    await message.answer("id має бути числом.")
    return

  reply_text = parts[2].strip()
  ticket = await db.get_ticket(ticket_id)
  if not ticket:
    await message.answer("Заявку не знайдено.")
    return

  try:
    await message.bot.send_message(
      ticket.user_id,
      f"Відповідь по заявці #{ticket.id} від {(message.from_user.first_name or 'адмін')}:\n{reply_text}",
    )
  except Exception as exc:  # pragma: no cover - network
    logging.exception("Failed to send reply to user", exc_info=exc)
    await message.answer("Не вдалося надіслати відповідь користувачу.")
    return

  await db.mark_ticket_answered(ticket_id, message.from_user.id, reply_text)
  sender = (message.from_user.first_name or "").strip() or "адмін"
  await message.answer(f"Відповідь надіслано користувачу @{ticket.username or 'користувач'} від {sender}.")

  # remove admin notifications about this ticket
  mappings = await db.get_ticket_messages(ticket_id)
  for m in mappings:
    try:
      await message.bot.delete_message(chat_id=m.chat_id, message_id=m.message_id)
    except Exception:
      logging.exception("Failed to delete ticket message %s", m.message_id)
  await db.delete_ticket_messages(ticket_id)


@router.message(Command("del_ticket"))
@_require_admin
async def cmd_del_ticket(message: Message, **_):
  parts = message.text.split(maxsplit=1)
  if len(parts) < 2:
    await message.answer("Використання: /del_ticket <id>")
    return

  try:
    ticket_id = int(parts[1])
  except ValueError:
    await message.answer("id має бути числом.")
    return

  ticket = await db.get_ticket(ticket_id)
  if not ticket:
    await message.answer("Заявку не знайдено.")
    return

  if await db.delete_ticket(ticket_id):
    mappings = await db.get_ticket_messages(ticket_id)
    for m in mappings:
      try:
        await message.bot.delete_message(chat_id=m.chat_id, message_id=m.message_id)
      except Exception:
        logging.exception("Failed to delete ticket message %s", m.message_id)
    await db.delete_ticket_messages(ticket_id)
    await message.answer(f"Заявку #{ticket_id} видалено. Вона більше не відображається у адмінів.")
  else:
    await message.answer("Не вдалося видалити заявку. Спробуйте пізніше.")


@router.message(Command("ban"))
@_require_admin
async def cmd_ban(message: Message, **_):
  parts = message.text.split(maxsplit=3)
  if len(parts) < 3:
    await message.answer("Використання: /ban <user_id> <хвилини> <причина>")
    return

  try:
    user_id = int(parts[1])
    minutes = int(parts[2])
  except ValueError:
    await message.answer("user_id та хвилини мають бути числами.")
    return

  reason = parts[3] if len(parts) > 3 else "без причини"
  until = datetime.now().astimezone() + timedelta(minutes=minutes)

  ok = await db.set_support_ban(user_id, until, reason)
  if ok:
    await message.answer(f"Користувача {user_id} заблоковано на {minutes} хв. Причина: {reason}")
    try:
      await message.bot.send_message(
        user_id,
        f"Вас заблоковано для створення заявок до {until.strftime('%d.%m %H:%M')}.\nПричина: {reason}",
      )
    except Exception:
      logging.exception("Failed to notify user about ban")
  else:
    await message.answer("Не вдалося встановити бан.")


@router.message(Command("unban"))
@_require_admin
async def cmd_unban(message: Message, **_):
  parts = message.text.split(maxsplit=1)
  if len(parts) < 2:
    await message.answer("Використання: /unban <user_id>")
    return

  try:
    user_id = int(parts[1])
  except ValueError:
    await message.answer("user_id має бути числом.")
    return

  if await db.remove_support_ban(user_id):
    await message.answer(f"Бан для {user_id} знято.")
    try:
      await message.bot.send_message(user_id, "Ваш бан знято. Ви можете знову створювати заявки.")
    except Exception:
      logging.exception("Failed to notify user about unban")
  else:
    await message.answer("Не вдалося зняти бан або користувача не було у бані.")
