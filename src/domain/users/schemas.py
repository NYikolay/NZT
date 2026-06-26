from pydantic import BaseModel


class TelegramProviderUser(BaseModel):
    id: int
    is_bot: bool
    first_name: str
    url: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    is_premium: bool | None = None
    added_to_attachment_menu: bool | None = None


class TelegramProviderTokenPayload(BaseModel):
    telegram_id: int
    user_id: int
