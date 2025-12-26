from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, Text, func

from db.orm.base import Base


class SupportAdmin(Base):
  __tablename__ = "support_admins"

  tg_id = Column(BigInteger, primary_key=True, unique=True, nullable=False)
  is_primary = Column(Boolean, nullable=False, default=False)
  created_at = Column(DateTime(timezone=True), server_default=func.now())


class SupportTicket(Base):
  __tablename__ = "support_tickets"

  id = Column(Integer, primary_key=True, autoincrement=True)
  user_id = Column(BigInteger, nullable=False)
  username = Column(Text, nullable=True)
  message = Column(Text, nullable=False)
  status = Column(Text, nullable=False, default="open")
  answer_text = Column(Text, nullable=True)
  answered_by = Column(BigInteger, nullable=True)
  created_at = Column(DateTime(timezone=True), server_default=func.now())
  updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SupportBan(Base):
  __tablename__ = "support_bans"

  user_id = Column(BigInteger, primary_key=True)
  reason = Column(Text, nullable=True)
  until = Column(DateTime(timezone=True), nullable=True)
  created_at = Column(DateTime(timezone=True), server_default=func.now())


class SupportTicketMessage(Base):
  __tablename__ = "support_ticket_messages"

  id = Column(Integer, primary_key=True, autoincrement=True)
  ticket_id = Column(Integer, nullable=False)
  admin_id = Column(BigInteger, nullable=False)
  chat_id = Column(BigInteger, nullable=False)
  message_id = Column(BigInteger, nullable=False)
  created_at = Column(DateTime(timezone=True), server_default=func.now())
