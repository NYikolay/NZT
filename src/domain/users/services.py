"""Services for the users domain."""

from typing import Literal
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.decorators import log_domain_operation
from src.domain.users.models import (
    User,
    UserIdentitiesProviders,
    ConnectionChannels,
)
from src.domain.users.repositories import (
    UserRepository,
    AuthIdentityRepository,
    ConnectionChannelRepository,
)
from src.domain.users.schemas import (
    TelegramProviderUser,
    UserCreate,
    UserUpdate,
    UserResponse,
    AuthIdentityCreate,
)

logger = structlog.get_logger()


class UserService:
    """Service for user management — login, registration, profile update."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._user_repo = UserRepository(session)
        self._auth_repo = AuthIdentityRepository(session)
        self._channel_repo = ConnectionChannelRepository(session)

    @log_domain_operation("get_user_by_telegram_id")
    async def get_user_by_telegram_id(self, telegram_id: int) -> type[User] | None:
        """Look up a User by their Telegram provider user ID.

        Returns the raw User model (not a schema) for use in auth dependencies,
        or None if no matching AuthIdentity exists.
        """
        identity = await self._auth_repo.get_by_provider_and_provider_user_id(
            provider=UserIdentitiesProviders.TELEGRAM,
            provider_user_id=str(telegram_id),
        )
        if identity is None:
            logger.info("telegram_identity_not_found", telegram_id=telegram_id)
            return None

        user = await self._user_repo.get_by_id(identity.user_id)
        if user is None:
            logger.warning(
                "user_not_found_for_identity",
                identity_id=str(identity.id),
                user_id=str(identity.user_id),
            )
            return None

        logger.debug(
            "user_found_by_telegram_id",
            user_id=str(user.id),
            telegram_id=telegram_id,
        )
        return user

    @log_domain_operation("get_user")
    async def get_user(self, user_id: UUID) -> UserResponse | None:
        """Retrieve a user by ID.

        Returns UserResponse or None if the user does not exist.
        """
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            logger.info("user_not_found", user_id=str(user_id))
            return None
        logger.debug("user_found", user_id=str(user_id))
        return UserResponse.model_validate(user)

    @log_domain_operation("update_user")
    async def update_user(
        self,
        user_id: UUID,
        update_data: UserUpdate,
    ) -> UserResponse | None:
        """Update a user's profile fields.

        Only the fields explicitly set on *update_data* are applied.
        Returns the updated UserResponse or None if the user does not exist.
        """
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            logger.warning("user_not_found", user_id=str(user_id))
            return None

        update_dict = update_data.model_dump(exclude_none=True)
        if not update_dict:
            logger.info("no_fields_to_update", user_id=str(user_id))
            return UserResponse.model_validate(user)

        updated = await self._user_repo.update(user, update_dict)
        logger.info(
            "user_updated",
            user_id=str(user_id),
            fields=list(update_dict.keys()),
        )
        return UserResponse.model_validate(updated)

    @log_domain_operation("get_or_create_user_from_telegram")
    async def get_or_create_user_from_telegram(
        self,
        telegram_user: TelegramProviderUser,
    ) -> tuple[UserResponse, Literal["created", "already_registered"]]:
        """Core login/registration flow for Telegram users.

        1. Look up an existing AuthIdentity for (TELEGRAM, telegram_user.id).
        2. If found → update the existing user's profile and return it.
        3. If not found → create a new user, auth identity, and connection channel atomically.
        4. Return a tuple of (UserResponse, status) where status indicates
           whether the user was just created or already existed.
        """
        provider_user_id = str(telegram_user.id)
        existing_identity = await self._auth_repo.get_by_provider_and_provider_user_id(
            provider=UserIdentitiesProviders.TELEGRAM,
            provider_user_id=provider_user_id,
        )

        if existing_identity is not None:
            logger.info(
                "existing_telegram_identity_found",
                user_id=str(existing_identity.user_id),
                telegram_id=provider_user_id,
            )
            user_response = await self._handle_existing_identity(
                existing_identity.user_id,
                telegram_user,
            )
            return user_response, "already_registered"

        logger.info(
            "no_existing_telegram_identity",
            telegram_id=provider_user_id,
        )
        user_response = await self._create_new_telegram_user(
            telegram_user, provider_user_id
        )
        return user_response, "created"

    async def _handle_existing_identity(
        self,
        user_id: UUID,
        telegram_user: TelegramProviderUser,
    ) -> UserResponse | None:
        """Update the existing user's profile from Telegram data."""
        update_data = self._map_telegram_user_to_update(telegram_user)
        return await self.update_user(user_id, update_data)

    async def _create_new_telegram_user(
        self,
        telegram_user: TelegramProviderUser,
        provider_user_id: str,
    ) -> UserResponse:
        """Create a new user, auth identity, and connection channel."""
        # 1. Create the user
        create_data = self._map_telegram_user_to_create(telegram_user)
        user = await self._user_repo.create(create_data.model_dump())

        # 2. Create the auth identity
        auth_create = AuthIdentityCreate(
            provider=UserIdentitiesProviders.TELEGRAM,
            provider_user_id=provider_user_id,
            profile=telegram_user.model_dump(),
            user_id=user.id,
        )

        await self._auth_repo.create(auth_create.model_dump())

        # 3. Create/update the connection channel
        await self._channel_repo.create_or_update(
            user_id=user.id,
            channel=ConnectionChannels.TELEGRAM,
        )

        logger.info(
            "new_telegram_user_created",
            user_id=str(user.id),
            telegram_id=provider_user_id,
        )
        return UserResponse.model_validate(user)

    @staticmethod
    def _map_telegram_user_to_create(telegram_user: TelegramProviderUser) -> UserCreate:
        """Map Telegram provider data to a UserCreate schema.

        * telegram_user.url → avatar_url
        * is_active is always True for new Telegram users
        """
        return UserCreate(
            first_name=telegram_user.first_name,
            username=telegram_user.username,
            is_active=True,
        )

    @staticmethod
    def _map_telegram_user_to_update(telegram_user: TelegramProviderUser) -> UserUpdate:
        """Map Telegram provider data to a UserUpdate schema.

        * telegram_user.url → avatar_url
        * Only fields that can change from the Telegram profile are included.
        """
        return UserUpdate(
            first_name=telegram_user.first_name,
            username=telegram_user.username,
            avatar_url=telegram_user.url,
        )
