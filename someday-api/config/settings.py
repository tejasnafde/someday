import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: str = "dev"

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    # No JWT secret — project uses RS256 JWKS verification.
    # JWKS URL is derived from SUPABASE_URL at runtime in auth_helper.py.

    # Database
    DATABASE_URL: str

    # Logging
    LOG_LEVEL: str = "DEBUG"

    # CORS
    ALLOWED_ORIGINS: str = "*"

    model_config = SettingsConfigDict(
        env_file=f".env.{os.getenv('APP_ENV', 'dev')}",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    def allowed_origins_list(self) -> list[str]:
        if self.ALLOWED_ORIGINS == "*":
            return ["*"]
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]


settings = Settings()
