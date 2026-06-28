"""Authentication and registration routes."""

from fastapi import APIRouter

from src.api.dependencies import SessionDep
from src.api.schemas.auth import RegisterRequest, RegisterResponse
from src.domain.users.services import UserService

auth_router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@auth_router.post(
    "/register",
    operation_id="RegisterUser",
    summary="Register a new user or return existing one",
    response_model=RegisterResponse,
    responses={
        200: {"description": "User already registered, profile updated"},
        201: {"description": "New user created"},
    },
)
async def register(
    session: SessionDep,
    body: RegisterRequest,
) -> RegisterResponse:
    """Register a user via their Telegram profile.

    Accepts the full ``TelegramProviderUser`` profile in the request body.
    If the user already exists their profile is updated and status is
    ``already_registered``. If the user is new, all required entities
    are created and status is ``created``.
    """
    service = UserService(session=session)
    user_response, status_flag = await service.get_or_create_user_from_telegram(
        body.telegram_profile
    )

    return RegisterResponse(
        status=status_flag,
        user=user_response,
    )
