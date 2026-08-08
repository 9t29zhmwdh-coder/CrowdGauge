"""Provider selection.

The registry is the only place that knows which concrete providers exist. Adding
a source means adding one adapter plus one branch here, nothing above this layer
changes.
"""

from crowdgauge.config import (
    KNOWN_PROVIDERS,
    PROVIDER_AUTO,
    PROVIDER_BESTTIME,
    PROVIDER_DEMO,
    PROVIDER_SERPAPI,
    Settings,
)
from crowdgauge.errors import ProviderNotConfigured
from crowdgauge.providers.base import BusynessProvider
from crowdgauge.providers.besttime import BestTimeProvider
from crowdgauge.providers.demo import DemoProvider
from crowdgauge.providers.serpapi import SerpApiProvider
from crowdgauge.texts import DEFAULT_LANGUAGE, text


def build_provider(
    settings: Settings, requested: str | None = None, language: str = DEFAULT_LANGUAGE
) -> BusynessProvider:
    """Return the provider to use for this request.

    A request may name a provider explicitly. Without that, the configured
    default applies, and "auto" resolves to the first provider that has
    credentials, falling back to the demo source.
    """
    choice = (requested or settings.provider or PROVIDER_AUTO).strip().lower()
    if choice == PROVIDER_AUTO:
        choice = settings.configured_providers()[0]
    if choice not in KNOWN_PROVIDERS:
        raise ProviderNotConfigured(
            f"Unknown provider '{choice}'. Available: {', '.join(KNOWN_PROVIDERS)}."
        )
    return _instantiate(choice, settings, language)


def _instantiate(choice: str, settings: Settings, language: str) -> BusynessProvider:
    if choice == PROVIDER_SERPAPI:
        return _build_serpapi(settings, language)
    if choice == PROVIDER_BESTTIME:
        return _build_besttime(settings, language)
    return DemoProvider(timeout=settings.request_timeout, language=language)


def _build_serpapi(settings: Settings, language: str) -> BusynessProvider:
    if not settings.has_serpapi():
        raise ProviderNotConfigured(
            "SerpApi needs CROWDGAUGE_SERPAPI_KEY. Get a key at https://serpapi.com/."
        )
    return SerpApiProvider(
        api_key=settings.serpapi_key.get_secret_value(),
        timeout=settings.request_timeout,
        language=language,
    )


def _build_besttime(settings: Settings, language: str) -> BusynessProvider:
    if not settings.has_besttime():
        raise ProviderNotConfigured(
            "BestTime.app needs CROWDGAUGE_BESTTIME_PRIVATE_KEY and "
            "CROWDGAUGE_BESTTIME_PUBLIC_KEY. Get both at https://besttime.app/."
        )
    return BestTimeProvider(
        private_key=settings.besttime_private_key.get_secret_value(),
        public_key=settings.besttime_public_key.get_secret_value(),
        timeout=settings.request_timeout,
        language=language,
    )


def provider_status(
    settings: Settings, language: str = DEFAULT_LANGUAGE
) -> list[dict[str, object]]:
    """Describe every provider for the interface, without exposing key material."""
    return [
        {
            "name": PROVIDER_SERPAPI,
            "label": SerpApiProvider.display_name,
            "configured": settings.has_serpapi(),
            "supports_live": SerpApiProvider.supports_live,
            "source": text("source_serpapi", language),
        },
        {
            "name": PROVIDER_BESTTIME,
            "label": BestTimeProvider.display_name,
            "configured": settings.has_besttime(),
            "supports_live": BestTimeProvider.supports_live,
            "source": text("source_besttime", language),
        },
        {
            "name": PROVIDER_DEMO,
            "label": DemoProvider.display_name,
            "configured": True,
            "supports_live": DemoProvider.supports_live,
            "source": text("source_demo", language),
        },
    ]
