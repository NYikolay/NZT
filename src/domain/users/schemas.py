from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime

from src.domain.users.models import (
    UserIdentitiesProviders,
    ConnectionChannels,
    UserRoles,
)


class TelegramProviderUser(BaseModel):
    id: int
    is_bot: bool
    first_name: str
    url: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    is_premium: bool | None = None
    added_to_attachment_menu: bool | None = None


class TelegramProviderTokenPayload(BaseModel):
    telegram_id: int
    user_id: int


class AuthIdentityCreate(BaseModel):
    provider: UserIdentitiesProviders
    provider_user_id: str
    profile: dict


class AuthIdentityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    user_id: UUID
    provider: UserIdentitiesProviders
    provider_user_id: str
    profile: dict


class ConnectionChannelCreate(BaseModel):
    channel: ConnectionChannels


class ConnectionChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    channel: ConnectionChannels
    first_seen_at: datetime
    last_seen_at: datetime


class UserCreate(BaseModel):
    first_name: str | None = None
    username: str | None = None
    avatar_url: str | None = None
    country: str | None = None
    is_active: bool = False


class UserUpdate(BaseModel):
    first_name: str | None = None
    username: str | None = None
    avatar_url: str | None = None
    country: str | None = None
    mobile_phone: str | None = None
    address: str | None = None
    time_zone: str | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str | None = None
    username: str | None = None
    avatar_url: str | None = None
    role: UserRoles
    is_active: bool
