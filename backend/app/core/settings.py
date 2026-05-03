from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(default="")
    webapp_url: str = Field(default="http://localhost:5173")
    public_base_url: str = Field(default="http://localhost:8000")
    webhook_secret: str = Field(default="dev-secret")

    database_url: str = Field(
        default="postgresql+asyncpg://printscout:printscout@localhost:5432/printscout"
    )

    thingiverse_token: str = Field(default="")
    myminifactory_key: str = Field(default="")

    # Dev only — skip Telegram initData validation and act as this Telegram user id.
    # MUST be 0 in production. Loud warning is logged at startup if non-zero.
    dev_fake_user_id: int = Field(default=0)

    @property
    def webhook_path(self) -> str:
        return "/telegram/webhook"

    @property
    def webhook_url(self) -> str:
        return f"{self.public_base_url.rstrip('/')}{self.webhook_path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
