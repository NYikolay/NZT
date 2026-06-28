"""Pydantic schemas for authentication and registration."""

from typing import Literal

from pydantic import BaseModel

from src.domain.users.schemas import TelegramProviderUser, UserResponse


class RegisterRequest(BaseModel):
    """Request body for user registration.

    Attributes:
        telegram_profile: The full Telegram user profile data.
    """

    telegram_profile: TelegramProviderUser


class RegisterResponse(BaseModel):
    """Response returned after a user registration attempt.

    Attributes:
        status: Indicates whether a new user was created or already existed.
        user: The resulting user profile.
    """

    status: Literal["created", "already_registered"]
    user: UserResponse
