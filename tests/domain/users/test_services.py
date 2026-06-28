"""Tests for users domain services."""

from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.users.models import (
    User,
    AuthIdentity,
    UserIdentitiesProviders,
    ConnectionChannels,
    UserRoles,
)
from src.domain.users.services import UserService
from src.domain.users.schemas import (
    TelegramProviderUser,
    UserCreate,
    UserUpdate,
    UserResponse,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def service(mock_session):
    return UserService(session=mock_session)


@pytest.fixture
def telegram_user() -> TelegramProviderUser:
    return TelegramProviderUser(
        id=12345,
        is_bot=False,
        first_name="John",
        url="https://t.me/johndoe",
        last_name="Doe",
        username="johndoe",
        language_code="en",
        is_premium=True,
    )


# ---------------------------------------------------------------------------
# _map_telegram_user_to_create tests
# ---------------------------------------------------------------------------


class TestMapTelegramUserToCreate:
    """Tests for _map_telegram_user_to_create static method."""

    def test_should_create_user_create_with_telegram_data(self, telegram_user):
        """Should map TelegramProviderUser to UserCreate correctly."""
        result = UserService._map_telegram_user_to_create(telegram_user)

        assert isinstance(result, UserCreate)
        assert result.first_name == "John"
        assert result.username == "johndoe"
        assert result.avatar_url == "https://t.me/johndoe"
        assert result.is_active is True

    def test_should_set_is_active_true(self, telegram_user):
        """is_active should always be True for new Telegram users."""
        result = UserService._map_telegram_user_to_create(telegram_user)

        assert result.is_active is True

    def test_should_handle_none_username(self):
        """Should handle Telegram user with no username."""
        user = TelegramProviderUser(
            id=99999,
            is_bot=False,
            first_name="NoUsername",
            url="https://t.me/nousername",
        )
        result = UserService._map_telegram_user_to_create(user)

        assert result.first_name == "NoUsername"
        assert result.username is None
        assert result.avatar_url == "https://t.me/nousername"


# ---------------------------------------------------------------------------
# _map_telegram_user_to_update tests
# ---------------------------------------------------------------------------


class TestMapTelegramUserToUpdate:
    """Tests for _map_telegram_user_to_update static method."""

    def test_should_map_telegram_data_to_update(self, telegram_user):
        """Should map TelegramProviderUser to UserUpdate correctly."""
        result = UserService._map_telegram_user_to_update(telegram_user)

        assert isinstance(result, UserUpdate)
        assert result.first_name == "John"
        assert result.username == "johndoe"
        assert result.avatar_url == "https://t.me/johndoe"
        # Should not include non-profile fields
        assert result.mobile_phone is None
        assert result.address is None
        assert result.time_zone is None

    def test_should_handle_none_username(self):
        """Should handle Telegram user with no username."""
        user = TelegramProviderUser(
            id=88888,
            is_bot=False,
            first_name="NoUser",
            url="https://t.me/nouser",
        )
        result = UserService._map_telegram_user_to_update(user)

        assert result.first_name == "NoUser"
        assert result.username is None
        assert result.avatar_url == "https://t.me/nouser"


# ---------------------------------------------------------------------------
# get_user tests
# ---------------------------------------------------------------------------


class TestGetUser:
    """Tests for get_user method."""

    @pytest.mark.asyncio
    async def test_should_return_user_when_found(self, service, mock_session):
        """get_user should return UserResponse when user exists."""
        user_id = uuid4()
        user = User(
            id=user_id,
            first_name="John",
            username="johndoe",
            role=UserRoles.USER,
            is_active=True,
        )
        mock_session.get = AsyncMock(return_value=user)

        result = await service.get_user(user_id)

        assert isinstance(result, UserResponse)
        assert result.id == user_id
        assert result.first_name == "John"
        assert result.username == "johndoe"
        assert result.role == UserRoles.USER
        assert result.is_active is True

    @pytest.mark.asyncio
    async def test_should_return_none_when_not_found(self, service, mock_session):
        """get_user should return None when user doesn't exist."""
        user_id = uuid4()
        mock_session.get = AsyncMock(return_value=None)

        result = await service.get_user(user_id)

        assert result is None


# ---------------------------------------------------------------------------
# update_user tests
# ---------------------------------------------------------------------------


class TestUpdateUser:
    """Tests for update_user method."""

    @pytest.mark.asyncio
    async def test_should_update_user_fields(self, service, mock_session):
        """Should update non-None fields and return updated UserResponse."""
        user_id = uuid4()
        user = User(
            id=user_id,
            first_name="OldName",
            username="olduser",
            role=UserRoles.USER,
            is_active=True,
        )
        mock_session.get = AsyncMock(return_value=user)

        update_data = UserUpdate(first_name="NewName", username="newuser")

        result = await service.update_user(user_id, update_data)

        assert isinstance(result, UserResponse)
        assert result.first_name == "NewName"
        assert result.username == "newuser"
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_return_none_when_user_not_found(self, service, mock_session):
        """Should return None when user doesn't exist."""
        user_id = uuid4()
        mock_session.get = AsyncMock(return_value=None)

        result = await service.update_user(
            user_id,
            UserUpdate(first_name="New"),
        )

        assert result is None
        mock_session.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_handle_no_fields_to_update(self, service, mock_session):
        """Should return current UserResponse when no fields to update."""
        user_id = uuid4()
        user = User(
            id=user_id,
            first_name="John",
            role=UserRoles.USER,
            is_active=True,
        )
        mock_session.get = AsyncMock(return_value=user)

        result = await service.update_user(user_id, UserUpdate())

        assert isinstance(result, UserResponse)
        assert result.first_name == "John"
        mock_session.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_only_update_provided_fields(self, service, mock_session):
        """Should only update fields that are explicitly set (not None)."""
        user_id = uuid4()
        user = User(
            id=user_id,
            first_name="John",
            username="johndoe",
            avatar_url="https://old.url",
            role=UserRoles.USER,
            is_active=True,
        )
        mock_session.get = AsyncMock(return_value=user)

        update_data = UserUpdate(first_name="Jane")

        result = await service.update_user(user_id, update_data)

        assert result.first_name == "Jane"
        assert result.username == "johndoe"  # unchanged
        assert result.avatar_url == "https://old.url"  # unchanged


# ---------------------------------------------------------------------------
# get_user_by_telegram_id tests
# ---------------------------------------------------------------------------


class TestGetUserByTelegramId:
    """Tests for get_user_by_telegram_id method."""

    @pytest.mark.asyncio
    async def test_should_return_user_when_identity_found(self, service, mock_session):
        """Should return User when AuthIdentity and User exist."""
        user_id = uuid4()
        user = User(
            id=user_id,
            first_name="John",
            username="johndoe",
            role=UserRoles.USER,
            is_active=True,
        )
        identity = AuthIdentity(
            user_id=user_id,
            provider=UserIdentitiesProviders.TELEGRAM,
            provider_user_id="12345",
        )

        # First execute call returns identity, second returns None (channel lookup not used here)
        mock_session.execute = AsyncMock()
        mock_session.execute.return_value.scalar_one_or_none = MagicMock(
            side_effect=[identity]
        )
        mock_session.get = AsyncMock(return_value=user)

        result = await service.get_user_by_telegram_id(12345)

        assert isinstance(result, User)
        assert result.id == user_id
        assert result.first_name == "John"
        assert result.username == "johndoe"

    @pytest.mark.asyncio
    async def test_should_return_none_when_identity_not_found(
        self, service, mock_session
    ):
        """Should return None when no AuthIdentity exists for the telegram_id."""
        mock_session.execute = AsyncMock()
        mock_session.execute.return_value.scalar_one_or_none = MagicMock(
            return_value=None
        )

        result = await service.get_user_by_telegram_id(99999)

        assert result is None

    @pytest.mark.asyncio
    async def test_should_return_none_when_user_not_found(self, service, mock_session):
        """Should return None when AuthIdentity exists but User does not."""
        identity = AuthIdentity(
            user_id=uuid4(),
            provider=UserIdentitiesProviders.TELEGRAM,
            provider_user_id="12345",
        )

        mock_session.execute = AsyncMock()
        mock_session.execute.return_value.scalar_one_or_none = MagicMock(
            side_effect=[identity]
        )
        mock_session.get = AsyncMock(return_value=None)

        result = await service.get_user_by_telegram_id(12345)

        assert result is None


# ---------------------------------------------------------------------------
# get_or_create_user_from_telegram tests
# ---------------------------------------------------------------------------


class TestGetOrCreateUserFromTelegram:
    """Tests for get_or_create_user_from_telegram — the core orchestration method."""

    @pytest.mark.asyncio
    async def test_should_update_existing_user_when_identity_found(
        self, service, mock_session, telegram_user
    ):
        """Should update existing user when AuthIdentity is found."""
        user_id = uuid4()
        existing_user = User(
            id=user_id,
            first_name="OldName",
            username="olduser",
            role=UserRoles.USER,
            is_active=True,
        )
        identity = AuthIdentity(
            user_id=user_id,
            provider=UserIdentitiesProviders.TELEGRAM,
            provider_user_id="12345",
        )

        # Mock: get_by_provider_and_provider_user_id returns an identity
        mock_session.execute = AsyncMock()
        mock_session.execute.return_value.scalar_one_or_none = MagicMock(
            side_effect=[identity, None]  # first for auth lookup
        )
        # Mock: get_by_id returns the existing user
        mock_session.get = AsyncMock(return_value=existing_user)

        result, status = await service.get_or_create_user_from_telegram(telegram_user)

        assert isinstance(result, UserResponse)
        assert result.first_name == "John"
        assert result.username == "johndoe"
        assert result.avatar_url == "https://t.me/johndoe"
        assert status == "already_registered"
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_create_new_user_when_identity_not_found(
        self, service, mock_session, telegram_user
    ):
        """Should create user + auth identity + channel when no existing identity."""
        user_id = uuid4()

        # Mock: get_by_provider_and_provider_user_id returns None (no existing identity)
        mock_session.execute = AsyncMock()
        mock_session.execute.return_value.scalar_one_or_none = MagicMock(
            side_effect=[None, None]  # first for auth lookup, second for channel lookup
        )

        # Patch _user_repo.create to return a proper User with id and role
        async def _fake_create(user_data: dict) -> User:
            return User(
                id=user_id,
                first_name=user_data.get("first_name"),
                username=user_data.get("username"),
                avatar_url=user_data.get("avatar_url"),
                is_active=user_data.get("is_active", False),
                role=UserRoles.USER,
            )

        service._user_repo.create = _fake_create

        result, status = await service.get_or_create_user_from_telegram(telegram_user)

        assert isinstance(result, UserResponse)
        assert result.id == user_id
        assert result.first_name == "John"
        assert result.username == "johndoe"
        assert result.is_active is True
        assert status == "created"
        # Should call add 2 times: auth_identity + connection_channel
        # (user is created via patched _fake_create without touching mock session)
        assert mock_session.add.call_count == 2
        assert mock_session.flush.await_count == 2

    @pytest.mark.asyncio
    async def test_should_create_auth_identity_with_full_profile(
        self, service, mock_session, telegram_user
    ):
        """AuthIdentity should store the full TelegramUser profile."""
        user_id = uuid4()

        mock_session.execute = AsyncMock()
        mock_session.execute.return_value.scalar_one_or_none = MagicMock(
            side_effect=[None, None]
        )

        # Patch _user_repo.create to return a proper User with id and role
        async def _fake_create(user_data: dict) -> User:
            return User(
                id=user_id,
                first_name=user_data.get("first_name"),
                username=user_data.get("username"),
                avatar_url=user_data.get("avatar_url"),
                is_active=user_data.get("is_active", False),
                role=UserRoles.USER,
            )

        service._user_repo.create = _fake_create

        _, status = await service.get_or_create_user_from_telegram(telegram_user)
        assert status == "created"

        # Verify the auth identity was added with the correct profile
        add_calls = mock_session.add.call_args_list
        auth_identity_added = None
        for call in add_calls:
            args, _ = call
            if isinstance(args[0], AuthIdentity):
                auth_identity_added = args[0]
                break

        assert auth_identity_added is not None
        assert auth_identity_added.provider == UserIdentitiesProviders.TELEGRAM
        assert auth_identity_added.provider_user_id == "12345"
        assert auth_identity_added.profile["id"] == 12345
        assert auth_identity_added.profile["first_name"] == "John"

    @pytest.mark.asyncio
    async def test_should_create_connection_channel_for_telegram(
        self, service, mock_session, telegram_user
    ):
        """Should create a TELEGRAM connection channel for new users."""
        user_id = uuid4()

        mock_session.execute = AsyncMock()
        mock_session.execute.return_value.scalar_one_or_none = MagicMock(
            side_effect=[None, None]
        )

        # Patch _user_repo.create to return a proper User with id and role
        async def _fake_create(user_data: dict) -> User:
            return User(
                id=user_id,
                first_name=user_data.get("first_name"),
                username=user_data.get("username"),
                avatar_url=user_data.get("avatar_url"),
                is_active=user_data.get("is_active", False),
                role=UserRoles.USER,
            )

        service._user_repo.create = _fake_create

        _, status = await service.get_or_create_user_from_telegram(telegram_user)
        assert status == "created"

        # Verify the connection channel was added
        add_calls = mock_session.add.call_args_list
        channel_added = None
        for call in add_calls:
            args, _ = call
            if hasattr(args[0], "channel") and hasattr(args[0], "user_id"):
                channel_added = args[0]
                break

        assert channel_added is not None
        assert channel_added.channel == ConnectionChannels.TELEGRAM
