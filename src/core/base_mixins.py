from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy import func, DateTime
from sqlalchemy.orm import Mapped, mapped_column


class UUIDMixin:
    """Миксин для UUID первичного ключа"""

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, doc="Unique UUID primary key v4"
    )


class IDMixin:
    """Default object unique ID generation"""

    id: Mapped[int] = mapped_column(primary_key=True)


class TimestampMixin:
    """Миксин для временных меток"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        doc="Object creation time (UTC).",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        server_onupdate=func.now(),
        doc="Object update time (UTC).",
    )
