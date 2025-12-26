import logging

from aiogram import F, Router
from aiogram.types import Message

import db.orm.utils as db

router = Router()


@router.message(F.text)
async def create_ticket_handler(message: Message):
  # ban check
  ban = await db.get_active_ban(message.from_user.id)
  if ban:
    until_str = ban.until.strftime("%d.%m %H:%M") if ban.until else "без дати завершення"
    await message.answer(f"Ви заблоковані для створення заявок до {until_str}.\nПричина: {ban.reason or 'не вказано'}.")
    return

  allowed, wait_seconds = await db.can_create_ticket(message.from_user.id, cooldown_minutes=30)
  if not allowed:
    mins = (wait_seconds + 59) // 60
    await message.answer(f"Можна створювати лише одну заявку кожні 30 хв. Спробуйте через ~{mins} хв.")
    return

  text = (message.text or "").strip()
  if not text:
    return

  ticket = await db.create_support_ticket(
    user_id=message.from_user.id,
    username=message.from_user.username,
    message=text,
  )

  if not ticket:
    await message.answer("Не вдалося створити заявку. Спробуйте пізніше.")
    return

  await message.answer(f"Створили заявку #{ticket.id}. Ми надішлемо відповідь тут.")

  admins = await db.list_support_admin_ids()
  if not admins:
    return

  for admin_id in admins:
    try:
      sent = await message.bot.send_message(
        admin_id,
        (
          f"Нова заявка #{ticket.id}\n"
          f"Від: @{message.from_user.username or 'користувач'} (id {message.from_user.id})\n\n"
          f"{text}\n\n"
          f"Відповісти: /reply {ticket.id} <текст>"
        ),
      )
      await db.save_ticket_message(ticket.id, admin_id, admin_id, sent.message_id)
    except Exception:  # pragma: no cover - network
      logging.exception("Failed to notify admin about ticket")
