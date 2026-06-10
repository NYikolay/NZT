import typing
from typing import List

from src.core.base_model import Base

from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import relationship

if typing.TYPE_CHECKING:
    from src.domain.memory.models import Event, RawMessage


class User(Base):
    __table__tablename__ = "users"

    events: Mapped[List["Event"]] = relationship(back_populates="user")
    raw_messages: Mapped[list["RawMessage"]] = relationship(back_populates="user")
