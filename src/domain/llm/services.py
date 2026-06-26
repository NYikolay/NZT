from typing import List, Dict

from openrouter import OpenRouter

from src.core.config import settings


async def get_llm_response(
    message: str,
    context_messages: List[Dict[str, str]] | None = None,
    model: str = "nvidia/nemotron-3-nano-30b-a3b:free",
):
    if context_messages is None:
        context_messages = []

    async with OpenRouter(api_key=settings.OPEN_ROUTER_API_KEY) as client:
        response = await client.chat.send_async(
            model=model,
            messages=[
                *context_messages,
                {"role": "user", "content": message},
            ],
        )

    return response.choices[0].message.content
