"""Repositories for the users domain."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.users.models import (
    User,
    AuthIdentity,
    ConnectionChannel,
    UserIdentitiesProviders,
    ConnectionChannels,
)


class UserRepository:
    """Repository for User CRUD."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, user_data: dict) -> User:
        user = User(**user_data)
        self.session.add(user)
        await self.session.flush()
        return user

    async def update(self, user: User, update_data: dict) -> User:
        for key, value in update_data.items():
            setattr(user, key, value)
        await self.session.flush()
        return user


class AuthIdentityRepository:
    """Repository for AuthIdentity CRUD."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_provider_and_provider_user_id(
        self,
        provider: UserIdentitiesProviders,
        provider_user_id: str,
    ) -> AuthIdentity | None:
        stmt = select(AuthIdentity).where(
            AuthIdentity.provider == provider,
            AuthIdentity.provider_user_id == provider_user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, auth_data: dict) -> AuthIdentity:
        auth = AuthIdentity(**auth_data)
        self.session.add(auth)
        await self.session.flush()
        return auth


class ConnectionChannelRepository:
    """Repository for ConnectionChannel CRUD."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_or_update(
        self,
        user_id: UUID,
        channel: ConnectionChannels,
    ) -> ConnectionChannel:
        stmt = select(ConnectionChannel).where(
            ConnectionChannel.user_id == user_id,
            ConnectionChannel.channel == channel,
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is not None:
            # Touch updated_at/last_seen_at via the model's onupdate hook
            existing.channel = channel
            await self.session.flush()
            return existing

        conn = ConnectionChannel(user_id=user_id, channel=channel)
        self.session.add(conn)
        await self.session.flush()
        return conn
