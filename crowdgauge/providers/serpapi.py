"""SerpApi adapter: Google Maps popular times, including the live value.

Google itself exposes popular times only in the Maps interface, never through
the Places API. The feature request for it has been open since 2017
(issuetracker.google.com/issues/35827550). SerpApi resolves Google Maps under
its own licence and hands the result over as JSON, which is why CrowdGauge
talks to SerpApi instead of scraping Google directly.

Busyness semantics: percentage of this venue's own peak, 100 means as busy as
it ever gets.
"""

import re

from crowdgauge.errors import BusynessUnavailable, VenueNotFound
from crowdgauge.models import (
    WEEKDAY_KEYS,
    BusynessReport,
    DayBusyness,
    HourBusyness,
    LiveBusyness,
    Venue,
    Weekday,
    empty_week,
)
from crowdgauge.providers.base import DEFAULT_SEARCH_LIMIT, BusynessProvider, normalise_query

SEARCH_URL = "https://serpapi.com/search.json"

# Matches "6 AM", "12 PM", "6 a.m." and the bare 24 hour form "18" that the
# non English locales return.
_TIME_PATTERN = re.compile(r"^\s*(\d{1,2})\s*(?:\.?\s*)?(a\.?m\.?|p\.?m\.?)?\s*$", re.IGNORECASE)

_LIVE_LABEL_KEYS = ("info", "live_info", "text")


class SerpApiProvider(BusynessProvider):
    """Reads Google Maps popular times through SerpApi."""

    name = "serpapi"
    display_name = "SerpApi (Google Maps)"
    attribution_key = "attribution_serpapi"
    supports_live = True

    def __init__(self, api_key: str, timeout: float = 20.0, language: str = "en") -> None:
        super().__init__(timeout=timeout, language=language)
        self._api_key = api_key

    async def search_venues(self, query: str, limit: int = DEFAULT_SEARCH_LIMIT) -> list[Venue]:
        params = self._base_params() | {"q": normalise_query(query), "type": "search"}
        payload = await self._get_json(SEARCH_URL, params)
        candidates = payload.get("local_results") or []
        if not candidates and isinstance(payload.get("place_results"), dict):
            candidates = [payload["place_results"]]
        venues = [self._to_venue(entry) for entry in candidates[:limit] if entry.get("place_id")]
        if not venues:
            raise VenueNotFound(f"Google Maps knows no place matching '{normalise_query(query)}'.")
        return venues

    async def fetch_report(self, venue: Venue) -> BusynessReport:
        params = self._base_params() | {"place_id": venue.provider_venue_id, "type": "place"}
        payload = await self._get_json(SEARCH_URL, params)
        place = payload.get("place_results") or {}
        popular = place.get("popular_times") or {}
        graph = popular.get("graph_results") or {}
        if not graph:
            raise BusynessUnavailable(
                f"Google reports no popular times for '{venue.name}'. "
                "This is normal for places with too few visits to aggregate."
            )
        return BusynessReport(
            venue=venue,
            provider=self.name,
            provider_label=self.display_name,
            attribution=self.attribution,
            days=self._parse_week(graph),
            live=self._parse_live(popular),
            typical_visit_duration=self._parse_visit_duration(popular, place),
            notes=self._build_notes(popular),
        )

    def _base_params(self) -> dict[str, str]:
        return {"engine": "google_maps", "api_key": self._api_key, "hl": self._language}

    def _to_venue(self, entry: dict) -> Venue:
        coordinates = entry.get("gps_coordinates") or {}
        return Venue(
            provider=self.name,
            provider_venue_id=str(entry.get("place_id", "")),
            name=str(entry.get("title") or entry.get("name") or "Unknown place"),
            address=entry.get("address"),
            latitude=coordinates.get("latitude"),
            longitude=coordinates.get("longitude"),
        )

    def _parse_week(self, graph: dict) -> list[DayBusyness]:
        """Fill a blank week from the per weekday hour lists SerpApi returns."""
        week = {day.weekday: day for day in empty_week()}
        for key, entries in graph.items():
            weekday = self._weekday_from_key(key)
            if weekday is None or not isinstance(entries, list):
                continue
            week[weekday] = DayBusyness(weekday=weekday, hours=self._parse_hours(entries))
        return [week[Weekday(index)] for index in range(7)]

    def _parse_hours(self, entries: list) -> list[HourBusyness]:
        slots = {hour: HourBusyness(hour=hour) for hour in range(24)}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            hour = parse_hour_label(str(entry.get("time", "")))
            if hour is None:
                continue
            slots[hour] = HourBusyness(
                hour=hour,
                score=clamp_score(entry.get("busyness_score")),
                label=entry.get("info"),
            )
        return list(slots.values())

    @staticmethod
    def _weekday_from_key(key: str) -> Weekday | None:
        normalised = key.strip().lower()
        return Weekday(WEEKDAY_KEYS.index(normalised)) if normalised in WEEKDAY_KEYS else None

    def _parse_live(self, popular: dict) -> LiveBusyness | None:
        """Read the live value, which SerpApi has shipped under several keys."""
        live = popular.get("live_hash") or popular.get("live") or {}
        if not isinstance(live, dict):
            return None
        label = next(
            (live[key] for key in _LIVE_LABEL_KEYS if isinstance(live.get(key), str)), None
        )
        score = clamp_score(live.get("busyness_score") or live.get("live_busyness_score"))
        if label is None and score is None:
            return None
        return LiveBusyness(score=score, label=label)

    @staticmethod
    def _parse_visit_duration(popular: dict, place: dict) -> str | None:
        live = popular.get("live_hash") or {}
        candidate = live.get("time_spent") if isinstance(live, dict) else None
        return candidate or place.get("typical_time_spent") or popular.get("time_spent")

    def _build_notes(self, popular: dict) -> list[str]:
        notes = [self._note("note_share_of_peak"), self._note("note_google_origin")]
        if not self._parse_live(popular):
            notes.append(self._note("note_no_live_value"))
        return notes


def parse_hour_label(label: str) -> int | None:
    """Turn '6 AM', '12 PM' or a bare '18' into an hour between 0 and 23."""
    match = _TIME_PATTERN.match(label)
    if not match:
        return None
    hour = int(match.group(1))
    meridiem = (match.group(2) or "").replace(".", "").lower()
    if not meridiem:
        return hour if 0 <= hour <= 23 else None
    if not 1 <= hour <= 12:
        return None
    if meridiem == "am":
        return 0 if hour == 12 else hour
    return 12 if hour == 12 else hour + 12


def clamp_score(value: object) -> int | None:
    """Accept only numeric scores and keep them inside the documented 0 to 100."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return max(0, min(100, int(round(value))))
