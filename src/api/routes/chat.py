from fastapi import APIRouter

from src import settings
from src.api.dependencies import SessionDep, CurrentUser
from src.api.schemas.chat import ChatMessage
from src.api.tasks.tasks import consolidate_extracted_memory
from src.domain.extraction.services import extract_data
from src.domain.llm.services import get_final_user_response

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
async def send_chat_message(
    message: ChatMessage, session: SessionDep, user: CurrentUser
):
    extracted_message_data = await extract_data(
        api_key=settings.OPEN_ROUTER_API_KEY,
        message=message.message,
        session=session,
        user_id=user.id,
    )

    await consolidate_extracted_memory.kiq(
        user_id=user.id,
        raw_message=message.message,
        extracted_message_data=extracted_message_data,
    )

    llm_response = await get_final_user_response(message=message.message)

    return ChatMessage(message=llm_response)
