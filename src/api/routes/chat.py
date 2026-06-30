from fastapi import APIRouter

from src import settings
from src.api.dependencies import SessionDep
from src.api.schemas.chat import ChatMessage
from src.domain.extraction.services import extract_data
from src.api.tasks.echo_tasks import echo_task

chat_router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


@chat_router.post(
    "/send_message",
    operation_id="SendLLMMessage",
    summary="Send LLM message",
    response_model=ChatMessage,
)
async def send_chat_message(message: ChatMessage, session: SessionDep):
    await extract_data(
        api_key=settings.OPEN_ROUTER_API_KEY,
        message=message.message,
        session=session,
    )

    return ChatMessage(message="asdasd")


@chat_router.get(
    "/check",
    operation_id="Test",
    summary="Test",
)
async def echo_check_test():
    await echo_task.kiq(message="Hello world")
    return "OK"
