from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import HTTPException, Request, status, Depends

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.exc import IntegrityError


session_factory = async_sessionmaker(
    autoflush=False, autocommit=False, expire_on_commit=False
)


async def provide_transaction(
    request: Request,
) -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    async with session_factory(bind=request.app.state.engine) as session:
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
