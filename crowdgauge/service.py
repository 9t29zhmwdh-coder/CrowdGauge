"""Lookup orchestration between the web layer and the providers.

Holds the cache and the derived numbers the interface needs, so neither the
provider adapters nor the HTTP handlers have to care about either.
"""

from crowdgauge.cache import TTLCache
from crowdgauge.config import Settings
from crowdgauge.models import BusynessReport, DayBusyness, HourBusyness, Venue
from crowdgauge.providers.base import DEFAULT_SEARCH_LIMIT, BusynessProvider, normalise_query
from crowdgauge.providers.registry import build_provider
from crowdgauge.texts import DEFAULT_LANGUAGE


class LookupService:
    """Resolves a location query into a normalised busyness report."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cache = TTLCache(settings.cache_ttl)

    async def search(
        self,
        query: str,
        provider_name: str | None = None,
        limit: int = DEFAULT_SEARCH_LIMIT,
        language: str = DEFAULT_LANGUAGE,
    ) -> tuple[BusynessProvider, list[Venue]]:
        provider = build_provider(self._settings, provider_name, language)
        return provider, await provider.search_venues(normalise_query(query), limit=limit)

    async def report_for_query(
        self,
        query: str,
        provider_name: str | None = None,
        language: str = DEFAULT_LANGUAGE,
    ) -> BusynessReport:
        """Take the first search hit and return its report."""
        provider, venues = await self.search(query, provider_name, limit=1, language=language)
        return await self.report_for_venue(provider, venues[0])

    async def report_for_venue(self, provider: BusynessProvider, venue: Venue) -> BusynessReport:
        """Serve the weekly forecast from cache, refresh the live value every time.

        The language is part of the cache key: the same venue in German carries
        different note and attribution text than in English.
        """
        key = f"{provider.name}:{provider.language}:{venue.provider_venue_id}"
        cached = self._cache.get(key)
        if isinstance(cached, BusynessReport):
            return cached
        report = await provider.fetch_report(venue)
        self._cache.set(key, report)
        return report

    async def report_for_venue_id(
        self,
        venue_id: str,
        name: str,
        address: str | None,
        provider_name: str | None = None,
        language: str = DEFAULT_LANGUAGE,
    ) -> BusynessReport:
        """Rebuild a venue from what the search step handed to the frontend."""
        provider = build_provider(self._settings, provider_name, language)
        venue = Venue(
            provider=provider.name,
            provider_venue_id=venue_id,
            name=name,
            address=address,
        )
        return await self.report_for_venue(provider, venue)

    def clear_cache(self) -> None:
        self._cache.clear()


def busiest_hours(report: BusynessReport, count: int = 3) -> list[dict[str, object]]:
    """Return the highest scoring slots of the week, busiest first."""
    scored = [
        {"weekday": int(day.weekday), "hour": slot.hour, "score": slot.score}
        for day in report.days
        for slot in day.hours
        if slot.has_data
    ]
    scored.sort(key=lambda entry: entry["score"], reverse=True)
    return scored[:count]


def quietest_hours(report: BusynessReport, count: int = 3) -> list[dict[str, object]]:
    """Return the quietest open slots, which is what most users actually want."""
    scored = [
        {"weekday": int(day.weekday), "hour": slot.hour, "score": slot.score}
        for day in report.days
        for slot in day.hours
        if slot.has_data and (slot.score or 0) > 0
    ]
    scored.sort(key=lambda entry: entry["score"])
    return scored[:count]


def day_summary(day: DayBusyness) -> dict[str, object]:
    """Peak hour and mean score for one day, used for the weekday overview."""
    scored: list[HourBusyness] = [slot for slot in day.hours if slot.has_data]
    if not scored:
        return {"weekday": int(day.weekday), "peak_hour": None, "peak_score": None, "mean": None}
    peak = max(scored, key=lambda slot: slot.score or 0)
    mean = round(sum(slot.score or 0 for slot in scored) / len(scored))
    return {
        "weekday": int(day.weekday),
        "peak_hour": peak.hour,
        "peak_score": peak.score,
        "mean": mean,
    }
