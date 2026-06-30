from enum import Enum
import typing
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import List

from sqlalchemy import (
    String,
    Text,
    UniqueConstraint,
    func,
    DateTime,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.dialects.postgresql import JSON

from src.core.base_model import Base
from src.domain.users.models_mixins import UserOwnedMixin
from src.core.base_mixins import UUIDMixin, TimestampMixin

if typing.TYPE_CHECKING:
    from src.domain.memory.models import (
        Event,
        RawMessage,
        Entity,
        RelationshipHistory,
        EntityRelationTypeSuggestion,
    )


DEFAULT_USER_RELATION_NAME = "user"


class UserRoles(str, Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class UserIdentitiesProviders(str, Enum):
    VK = "VK"
    EMAIL = "email"
    GOOGLE = "google"
    INSTAGRAM = "instagram"
    TELEGRAM = "telegram"
    APPLE = "apple"


class ConnectionChannels(str, Enum):
    PHONE = "phone"
    WEB = "web"
    TELEGRAM = "telegram"
    DESKTOP = "desktop"


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    time_zone: Mapped[str | None] = mapped_column(String(100), doc="User timezone")
    first_name: Mapped[str | None] = mapped_column(String(100), doc="User First Name")
    country: Mapped[str | None] = mapped_column(String(100), doc="User Last Name")
    username: Mapped[str | None] = mapped_column(
        String(65), unique=True, doc="User username"
    )
    mobile_phone: Mapped[str | None] = mapped_column(
        String(16), doc="User mobile phone"
    )
    address: Mapped[str | None] = mapped_column(
        String(125), doc="User real address/location"
    )
    avatar_url: Mapped[str | None] = mapped_column(
        Text, doc="S3 or media server url profile photo"
    )
    role: Mapped[UserRoles] = mapped_column(
        default=UserRoles.USER, doc="User role. Default is User"
    )
    is_active: Mapped[bool] = mapped_column(default=False)

    events: Mapped[List["Event"]] = relationship(
        back_populates=DEFAULT_USER_RELATION_NAME,
    )
    entities: Mapped[List["Entity"]] = relationship(
        back_populates=DEFAULT_USER_RELATION_NAME
    )
    raw_messages: Mapped[List["RawMessage"]] = relationship(
        back_populates=DEFAULT_USER_RELATION_NAME
    )
    relationships_history: Mapped[List["RelationshipHistory"]] = relationship(
        back_populates=DEFAULT_USER_RELATION_NAME
    )
    auth_identities: Mapped[List["AuthIdentity"]] = relationship(
        back_populates=DEFAULT_USER_RELATION_NAME
    )
    connection_channels: Mapped[List["ConnectionChannel"]] = relationship(
        back_populates=DEFAULT_USER_RELATION_NAME
    )
    entity_relation_type_suggestions: Mapped[List["EntityRelationTypeSuggestion"]] = (
        relationship(back_populates=DEFAULT_USER_RELATION_NAME)
    )

    def __repr__(self):
        return f"User with id: {self.id} and username {self.username}"

    @validates("avatar_url")
    def validate_avatar_url(self, key: str, url: str):
        """Валидация URL"""

        value = url.strip()
        parsed = urlparse(value)

        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Только http/https: {parsed.scheme}")

        if not parsed.netloc:
            raise ValueError("URL должен содержать хост")

        return value


class AuthIdentity(Base, UUIDMixin, TimestampMixin, UserOwnedMixin):
    __tablename__ = "auth_identities"

    provider: Mapped[UserIdentitiesProviders]
    provider_user_id: Mapped[str]
    profile: Mapped[JSON] = mapped_column(JSON, default=lambda: {})

    __table_args__ = (
        UniqueConstraint("user_id", "provider_user_id", name="uq_user_provider"),
    )

    def __repr__(self):
        return f"User {self.user_id} auth identity for provider: {self.provider}"


class ConnectionChannel(Base, UUIDMixin, TimestampMixin, UserOwnedMixin):
    __tablename__ = "connection_channels"

    channel: Mapped[ConnectionChannels]
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        server_onupdate=func.now(),
    )
