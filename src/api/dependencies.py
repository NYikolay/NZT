import jwt
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import HTTPException, Request, status, Depends, Header
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from src.api.security import ALGORITHM
from src.domain.users.models import User
from src.core.config import settings
from src.core.database import create_session_factory
from src.domain.users.schemas import TelegramProviderTokenPayload


async def get_session_factory(
    request: Request,
) -> async_sessionmaker[AsyncSession]:
    """Provide a session factory bound to the app's engine."""
    return create_session_factory(engine=request.app.state.engine)


async def provide_transaction(
    request: Request,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide a session within a transaction boundary.

    Uses UnitOfWork-like pattern: the session is created per-request
    and transaction is automatically rolled back on unhandled errors.
    The caller must explicitly call ``await session.commit()`` to persist.
    """
    factory = create_session_factory(engine=request.app.state.engine)
    async with factory() as session:
        try:
            async with session.begin():
                yield session
        except IntegrityError as exc:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc


SessionDep = Annotated[AsyncSession, Depends(provide_transaction)]


async def get_current_user_tg_provider(
    session: SessionDep,
    authorization: Annotated[str, Header(description="Bearer {token}")],
) -> User | None:
    """Decode the JWT and return the matching User (or None if not found).

    TODO: Implement actual User lookup once UserRepository exists.
    """
    try:
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, settings.BOT_SECRET_TOKEN, algorithms=[ALGORITHM])
        token_data = TelegramProviderTokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    # Actually look up the user with selectinload to avoid N+1
    stmt = (
        select(User)
        .options(
            selectinload(User.events),
            selectinload(User.entities),
            selectinload(User.raw_messages),
            selectinload(User.relationships_history),
            selectinload(User.auth_identities),
            selectinload(User.connection_channels),
        )
        .where(User.id == token_data.user_id)  # TODO: map telegram_id -> user_id
    )
    result = await session.execute(stmt)
    user = result.scalars().first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user_tg_provider)]
