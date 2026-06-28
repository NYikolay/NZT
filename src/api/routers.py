from fastapi import APIRouter

from src.api.routes.auth import auth_router
from src.api.routes.chat import chat_router
from src.api.routes.health import health_router


def get_apps_router():
    """
    Main entrypoint of applications routers
    """
    router = APIRouter()
    router.include_router(health_router)
    router.include_router(chat_router)
    router.include_router(auth_router)
    return router
