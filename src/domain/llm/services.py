from openrouter import OpenRouter


class LLMConnector:
    def __init__(
        self,
        api_key: str,
        model: str | None = "deepseek/deepseek-v4-flash",
        context_messages=None,
    ):
        if context_messages is None:
            context_messages = []

        self.model = model
        self.context_messages = context_messages
        self.api_key = api_key

    async def chat_llm(self, message: str):
        async with OpenRouter(api_key=self.api_key) as client:
            response = await client.chat.send_async(
                model=self.model,
                messages=[*self.context_messages, {"role": "user", "content": message}],
            )

        return response.choices[0].message.content
