from typing import List, Any
from uuid import UUID

import structlog
from openrouter import OpenRouter
from openrouter.operations import CreateEmbeddingsData

from src import settings
from src.domain.decorators import log_domain_operation


logger = structlog.get_logger()


class LLMConnector:
    def __init__(
        self,
        api_key: str,
        model: str | None = "deepseek/deepseek-v4-flash:nitro",
        context_messages=None,
    ):
        if context_messages is None:
            context_messages = []

        self.model = model
        self.context_messages = context_messages
        self.api_key = api_key

    @log_domain_operation("_generate_embedding")
    async def chat_llm(
        self,
        message: str,
        temperature: float | None = 1.0,
        response_format: dict[str, Any] | None = None,
        max_tokens: int | None = None,
        plugins: List[dict[str, str]] | None = None,
        user_id: UUID | None = None,
        use_reasoning: bool = False,
    ):
        async with OpenRouter(api_key=self.api_key) as client:
            response = await client.chat.send_async(
                model=self.model,
                temperature=temperature,
                response_format=response_format,
                max_tokens=max_tokens,
                plugins=plugins,
                messages=[*self.context_messages, {"role": "user", "content": message}],
                user=user_id,
                reasoning={"exclude": True, "enabled": use_reasoning}
                if use_reasoning
                else None,
            )

        return response.choices[0].message.content

    @log_domain_operation("get_llm_embedding")
    async def get_llm_embedding(
        self,
        content: List[str],
        embedding_model: str = "openai/text-embedding-3-small",
        user_id: UUID | None = None,
    ) -> List[CreateEmbeddingsData]:
        async with OpenRouter(api_key=self.api_key) as client:
            response = await client.embeddings.generate_async(
                model=embedding_model, input=content, user=user_id
            )

        return response.data


@log_domain_operation("_generate_embedding")
async def get_final_user_response(message: str):
    connector = LLMConnector(api_key=settings.OPEN_ROUTER_API_KEY)

    return await connector.chat_llm(message=message, max_tokens=1000)
