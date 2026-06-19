import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: str = "dev"

    # Supabase — JWT verification uses ES256 JWKS derived from SUPABASE_URL
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str = ""  # admin API; used by mint_token.py for testing

    # Release pipeline (EAS build webhook → GitHub release)
    EAS_WEBHOOK_SECRET: str = ""
    GITHUB_TOKEN: str = ""

    # Database
    DATABASE_URL: str

    # Discord error alerts
    DISCORD_WEBHOOK_URL: str = ""

    # Web push (VAPID)
    VAPID_PUBLIC_KEY: str = ""
    VAPID_PRIVATE_KEY: str = ""
    VAPID_CONTACT_EMAIL: str = "hello@someday.app"

    # Logging
    LOG_LEVEL: str = "DEBUG"

    # CORS
    ALLOWED_ORIGINS: str = "*"

    # GitHub — used by the EAS build webhook to publish releases
    GITHUB_REPO: str = "tejasnafde/someday"

    model_config = SettingsConfigDict(
        env_file=f".env.{os.getenv('APP_ENV', 'dev')}",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    def allowed_origins_list(self) -> list[str]:
        if self.ALLOWED_ORIGINS == "*":
            return ["*"]
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]


settings = Settings()
