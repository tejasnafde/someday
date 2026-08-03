import json
import os

from pydantic_settings import BaseSettings, SettingsConfigDict


def load_config_blob() -> None:
    """Expand SOMEDAY_CONFIG, one JSON secret holding every credential.

    Secret Manager bills per secret version per month, not per byte, so eight
    secrets cost eight times what one JSON object holding the same eight values
    costs. Cloud Run can only map one secret to one env var, so the fan-out has
    to happen here.

    This must run at import time, before Settings() on the last line of this
    module. A FastAPI startup hook is too late: pydantic validates and raises
    there, not at first request.

    Existing environment variables win, so a locally exported value or a
    per-secret ref still overrides the blob. That keeps the switch reversible.

    In production the blob is mandatory. Without this check the safety net would
    be implicit and fragile: a deploy that forgets --set-secrets only fails
    because .dockerignore keeps .env.production out of the image, so pydantic
    finds nothing and raises. Add .env.production to the image and that silently
    becomes a service running on stale committed values instead. Fail here
    instead, where the reason is stated.
    """
    raw = os.environ.get("SOMEDAY_CONFIG")
    if not raw:
        if os.getenv("APP_ENV") == "production":
            raise RuntimeError(
                "SOMEDAY_CONFIG is not set but APP_ENV=production. The deploy "
                "must pass --set-secrets SOMEDAY_CONFIG=someday-api-config:latest."
            )
        return
    for key, value in json.loads(raw).items():
        os.environ.setdefault(key, str(value))


load_config_blob()


class Settings(BaseSettings):
    APP_ENV: str = "dev"

    # Supabase - JWT verification uses ES256 JWKS derived from SUPABASE_URL
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

    # Shared token guarding the Cloud Build → Discord push webhook
    CLOUDBUILD_ALERT_TOKEN: str = ""

    # Web push (VAPID)
    VAPID_PUBLIC_KEY: str = ""
    VAPID_PRIVATE_KEY: str = ""
    VAPID_CONTACT_EMAIL: str = "hello@someday.app"

    # Logging
    LOG_LEVEL: str = "DEBUG"

    # CORS
    ALLOWED_ORIGINS: str = "*"

    # GitHub - used by the EAS build webhook to publish releases
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
