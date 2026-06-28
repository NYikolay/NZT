import jwt
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import HTTPException, Request, status, Depends, Header
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.exc import IntegrityError

from src.api.exceptions import AuthenticationError
from src.api.security import ALGORITHM
from src.domain.users.models import User
from src.core.config import settings
from src.core.database import create_session_factory, UnitOfWork
from src.domain.users.schemas import TelegramProviderTokenPayload
from src.domain.users.services import UserService


async def get_session_factory(
    request: Request,
) -> async_sessionmaker[AsyncSession]:
    """Provide a session factory bound to the app's engine."""
    return create_session_factory(engine=request.app.state.engine)


async def provide_transaction(
    request: Request,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide a session within a transaction boundary.

    Uses the same implicit-transaction model as UnitOfWork: the session
    starts a transaction on first SQL operation. On exception the
    transaction is rolled back; the caller must explicitly call
    ``await session.commit()`` to persist changes.
    """
    factory = create_session_factory(engine=request.app.state.engine)
    async with factory() as session:
        try:
            yield session
        except IntegrityError as exc:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc


async def provide_uow(
    request: Request,
) -> AsyncGenerator[UnitOfWork, None]:
    """Provide a UnitOfWork bound to the app's engine.

    Use this dependency in routes that need the full UoW interface
    (e.g. when calling service-layer methods that expect a uow parameter).
    """
    factory = create_session_factory(engine=request.app.state.engine)
    async with UnitOfWork(factory) as uow:
        yield uow


SessionDep = Annotated[AsyncSession, Depends(provide_transaction)]
"""Dependency that injects an AsyncSession with implicit transaction management."""

UowDep = Annotated[UnitOfWork, Depends(provide_uow)]
"""Dependency that injects a UnitOfWork for service-layer integration."""


async def get_current_user_tg_provider(
    session: SessionDep,
    authorization: Annotated[str, Header(description="Bearer {token}")],
) -> User:
    """Decode the JWT and return the matching User model.

    If the user does not exist in the database, raises a 401 error
    instructing the caller to register first via POST /auth/register
    with a complete Telegram profile JWT.
    """
    try:
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, settings.BOT_SECRET_TOKEN, algorithms=[ALGORITHM])
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    token_payload = TelegramProviderTokenPayload(**payload)

    service = UserService(session=session)
    user = await service.get_user_by_telegram_id(token_payload.telegram_id)

    if user is None:
        raise AuthenticationError(
            message="User not registered. Call POST /auth/register with a complete Telegram profile JWT.",
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user_tg_provider)]
