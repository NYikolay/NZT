from fastapi import APIRouter

from src.api.dependencies import CurrentUser
from src.api.schemas.chat import ChatMessage
from src.domain.llm.services import get_llm_response

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
async def send_chat_message(message: ChatMessage, user: CurrentUser):
    answer = await get_llm_response(message.message)
    return ChatMessage(message=answer)
