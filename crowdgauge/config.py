"""Configuration loaded from environment variables and an optional .env file.

Keys live in the environment only. Nothing in this module writes a credential
to disk, to a log line or into an API response.
"""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROVIDER_AUTO = "auto"
PROVIDER_DEMO = "demo"
PROVIDER_SERPAPI = "serpapi"
PROVIDER_BESTTIME = "besttime"
PROVIDER_OPENDATA_CH = "opendata_ch"

KNOWN_PROVIDERS = (
    PROVIDER_SERPAPI,
    PROVIDER_BESTTIME,
    PROVIDER_OPENDATA_CH,
    PROVIDER_DEMO,
)


class Settings(BaseSettings):
    """Runtime configuration for the server and the providers."""

    model_config = SettingsConfigDict(
        env_prefix="CROWDGAUGE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    provider: str = PROVIDER_AUTO

    serpapi_key: SecretStr | None = None
    besttime_private_key: SecretStr | None = None
    besttime_public_key: SecretStr | None = None

    host: str = "127.0.0.1"
    port: int = Field(default=8734, ge=1, le=65535)
    cache_ttl: int = Field(default=900, ge=0, le=86400)
    request_timeout: float = Field(default=20.0, gt=0, le=120)

    def has_serpapi(self) -> bool:
        return _is_filled(self.serpapi_key)

    def has_besttime(self) -> bool:
        return _is_filled(self.besttime_private_key) and _is_filled(self.besttime_public_key)

    def configured_providers(self) -> list[str]:
        """Providers usable right now, in preference order.

        Keyed sources come first because they cover arbitrary venues. Swiss open
        data needs no key and returns measured counts, so it ranks above the
        synthetic demo source, which stays the last resort.
        """
        available = []
        if self.has_serpapi():
            available.append(PROVIDER_SERPAPI)
        if self.has_besttime():
            available.append(PROVIDER_BESTTIME)
        available.append(PROVIDER_OPENDATA_CH)
        available.append(PROVIDER_DEMO)
        return available


def _is_filled(secret: SecretStr | None) -> bool:
    """Treat an empty string like a missing key, because .env templates ship empty."""
    return secret is not None and bool(secret.get_secret_value().strip())


def load_settings() -> Settings:
    return Settings()
