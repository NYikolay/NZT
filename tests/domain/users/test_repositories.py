"""Tests for users domain repositories."""

from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.users.models import (
    User,
    AuthIdentity,
    ConnectionChannel,
    UserIdentitiesProviders,
    ConnectionChannels,
)
from src.domain.users.repositories import (
    UserRepository,
    AuthIdentityRepository,
    ConnectionChannelRepository,
)


# ---------------------------------------------------------------------------
# UserRepository tests
# ---------------------------------------------------------------------------


class TestUserRepository:
    """Tests for UserRepository."""

    @pytest.fixture
    def session(self):
        return AsyncMock()

    @pytest.fixture
    def repo(self, session):
        return UserRepository(session=session)

    @pytest.mark.asyncio
    async def test_should_get_user_by_id(self, repo, session):
        """get_by_id should return a User when found."""
        user_id = uuid4()
        expected = User(id=user_id, username="testuser")
        session.get = AsyncMock(return_value=expected)

        result = await repo.get_by_id(user_id)

        assert result is not None
        assert result.id == user_id
        assert result.username == "testuser"
        session.get.assert_awaited_once_with(User, user_id)

    @pytest.mark.asyncio
    async def test_should_return_none_when_user_not_found_by_id(self, repo, session):
        """get_by_id should return None when no user exists."""
        user_id = uuid4()
        session.get = AsyncMock(return_value=None)

        result = await repo.get_by_id(user_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_should_get_user_by_username(self, repo, session):
        """get_by_username should return a User when found."""
        expected = User(username="johndoe")
        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none = MagicMock(
            return_value=expected
        )

        result = await repo.get_by_username("johndoe")

        assert result is not None
        assert result.username == "johndoe"

    @pytest.mark.asyncio
    async def test_should_return_none_when_user_not_found_by_username(
        self, repo, session
    ):
        """get_by_username should return None when no user exists."""
        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

        result = await repo.get_by_username("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_should_create_user(self, repo, session):
        """create should add a new User and flush."""
        user_data = {
            "username": "newuser",
            "first_name": "New",
            "is_active": True,
        }

        result = await repo.create(user_data)

        assert isinstance(result, User)
        assert result.username == "newuser"
        assert result.first_name == "New"
        assert result.is_active is True
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_update_user(self, repo, session):
        """update should modify fields on a User and flush."""
        user = User(username="oldname")
        update_data = {"username": "newname", "first_name": "Updated"}

        result = await repo.update(user, update_data)

        assert result.username == "newname"
        assert result.first_name == "Updated"
        session.flush.assert_awaited_once()


# ---------------------------------------------------------------------------
# AuthIdentityRepository tests
# ---------------------------------------------------------------------------


class TestAuthIdentityRepository:
    """Tests for AuthIdentityRepository."""

    @pytest.fixture
    def session(self):
        return AsyncMock()

    @pytest.fixture
    def repo(self, session):
        return AuthIdentityRepository(session=session)

    @pytest.mark.asyncio
    async def test_should_get_by_provider_and_provider_user_id(self, repo, session):
        """Should find an existing identity by provider + provider_user_id."""
        expected = AuthIdentity(
            provider=UserIdentitiesProviders.TELEGRAM,
            provider_user_id="12345",
        )
        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none = MagicMock(
            return_value=expected
        )

        result = await repo.get_by_provider_and_provider_user_id(
            provider=UserIdentitiesProviders.TELEGRAM,
            provider_user_id="12345",
        )

        assert result is not None
        assert result.provider == UserIdentitiesProviders.TELEGRAM
        assert result.provider_user_id == "12345"

    @pytest.mark.asyncio
    async def test_should_return_none_when_identity_not_found(self, repo, session):
        """Should return None when no matching identity exists."""
        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

        result = await repo.get_by_provider_and_provider_user_id(
            provider=UserIdentitiesProviders.TELEGRAM,
            provider_user_id="99999",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_should_create_auth_identity(self, repo, session):
        """create should add a new AuthIdentity and flush."""
        auth_data = {
            "provider": UserIdentitiesProviders.TELEGRAM,
            "provider_user_id": "67890",
            "user_id": uuid4(),
            "profile": {"first_name": "Test"},
        }

        result = await repo.create(auth_data)

        assert isinstance(result, AuthIdentity)
        assert result.provider == UserIdentitiesProviders.TELEGRAM
        assert result.provider_user_id == "67890"
        assert result.profile == {"first_name": "Test"}
        session.add.assert_called_once()
        session.flush.assert_awaited_once()


# ---------------------------------------------------------------------------
# ConnectionChannelRepository tests
# ---------------------------------------------------------------------------


class TestConnectionChannelRepository:
    """Tests for ConnectionChannelRepository."""

    @pytest.fixture
    def session(self):
        return AsyncMock()

    @pytest.fixture
    def repo(self, session):
        return ConnectionChannelRepository(session=session)

    @pytest.mark.asyncio
    async def test_should_create_new_channel(self, repo, session):
        """Should create a new ConnectionChannel when none exists."""
        user_id = uuid4()
        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

        result = await repo.create_or_update(
            user_id=user_id,
            channel=ConnectionChannels.TELEGRAM,
        )

        assert isinstance(result, ConnectionChannel)
        assert result.user_id == user_id
        assert result.channel == ConnectionChannels.TELEGRAM
        session.add.assert_called_once()
        session.flush.assert_awaited()

    @pytest.mark.asyncio
    async def test_should_update_existing_channel(self, repo, session):
        """Should update an existing ConnectionChannel when found."""
        user_id = uuid4()
        existing = ConnectionChannel(
            user_id=user_id,
            channel=ConnectionChannels.TELEGRAM,
        )
        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none = MagicMock(
            return_value=existing
        )

        result = await repo.create_or_update(
            user_id=user_id,
            channel=ConnectionChannels.TELEGRAM,
        )

        assert result.user_id == user_id
        assert result.channel == ConnectionChannels.TELEGRAM
        session.add.assert_not_called()
        session.flush.assert_awaited()
