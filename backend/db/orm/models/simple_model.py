from db.orm.base import Base
from sqlalchemy import Column, Integer, BigInteger


class Subs(Base):
    __tablename__ = "secret_subs"

    id = Column(Integer, autoincrement=True)
    tg_id = Column(BigInteger, primary_key=True, unique=True, nullable=False)