"""BestTime.app adapter: footfall forecasts from anonymised phone signals.

This source is independent of Google, which matters for two reasons. It stays
available if Google changes its Maps output, and it covers venues Google has
too little data for. The numbers will not match Google's exactly, because the
underlying panel is different.

Credit model: creating a forecast costs more than querying one, and a live
call costs one credit. CrowdGauge therefore caches forecasts and never caches
live values.
"""

from crowdgauge.errors import BusynessUnavailable, UpstreamError
from crowdgauge.models import (
    BusynessReport,
    DayBusyness,
    HourBusyness,
    LiveBusyness,
    Venue,
    Weekday,
    empty_week,
)
from crowdgauge.providers.base import DEFAULT_SEARCH_LIMIT, BusynessProvider, normalise_query

FORECAST_URL = "https://besttime.app/api/v1/forecasts"
LIVE_URL = "https://besttime.app/api/v1/forecasts/live"

# BestTime reports a venue day starting at 06:00, so day_raw[0] is 6 AM and
# day_raw[23] is 5 AM of the following calendar day.
DAY_START_HOUR = 6


class BestTimeProvider(BusynessProvider):
    """Reads weekly forecasts and live footfall from BestTime.app."""

    name = "besttime"
    display_name = "BestTime.app"
    attribution_key = "attribution_besttime"
    supports_live = True

    def __init__(
        self, private_key: str, public_key: str, timeout: float = 20.0, language: str = "en"
    ) -> None:
        super().__init__(timeout=timeout, language=language)
        self._private_key = private_key
        self._public_key = public_key

    async def search_venues(self, query: str, limit: int = DEFAULT_SEARCH_LIMIT) -> list[Venue]:
        """Split the query into name and address without spending a credit.

        BestTime geocodes name and address itself during the forecast call, so a
        separate search request would only cost credits for the same result.
        """
        cleaned = normalise_query(query)
        name, _, address = cleaned.partition(",")
        if not name.strip():
            raise UpstreamError("Enter at least a venue name, ideally 'name, city'.")
        return [
            Venue(
                provider=self.name,
                provider_venue_id=cleaned,
                name=name.strip(),
                address=address.strip() or None,
            )
        ][:limit]

    async def fetch_report(self, venue: Venue) -> BusynessReport:
        payload = await self._post_json(FORECAST_URL, self._forecast_params(venue))
        analysis = payload.get("analysis")
        if not isinstance(analysis, list) or not analysis:
            raise BusynessUnavailable(
                f"BestTime has no footfall forecast for '{venue.name}'. "
                "Adding the city or street usually helps the geocoder."
            )
        return BusynessReport(
            venue=self._enrich_venue(venue, payload.get("venue_info")),
            provider=self.name,
            provider_label=self.display_name,
            attribution=self.attribution,
            days=self._parse_week(analysis),
            live=await self._fetch_live(venue),
            notes=self._build_notes(),
        )

    async def _fetch_live(self, venue: Venue) -> LiveBusyness | None:
        """Fetch the live value, tolerating venues that have no live coverage."""
        try:
            payload = await self._post_json(LIVE_URL, self._live_params(venue))
        except UpstreamError:
            return None
        analysis = payload.get("analysis")
        if not isinstance(analysis, dict) or not analysis.get("venue_live_busyness_available"):
            return None
        return LiveBusyness(
            score=_clamp(analysis.get("venue_live_busyness")),
            delta_to_typical=_as_int(analysis.get("venue_live_forecasted_delta")),
            label=analysis.get("venue_live_busyness_label"),
        )

    def _forecast_params(self, venue: Venue) -> dict[str, str]:
        """Creating a forecast requires the private key."""
        return {"api_key_private": self._private_key} | self._venue_params(venue)

    def _live_params(self, venue: Venue) -> dict[str, str]:
        """Live lookups are read only and use the public key."""
        return {"api_key_public": self._public_key} | self._venue_params(venue)

    def _venue_params(self, venue: Venue) -> dict[str, str]:
        params = {"venue_name": venue.name}
        if venue.address:
            params["venue_address"] = venue.address
        return params

    def _parse_week(self, analysis: list) -> list[DayBusyness]:
        """Project every day_raw array onto calendar days, hour by hour."""
        slots: dict[tuple[int, int], HourBusyness] = {}
        for entry in analysis:
            if isinstance(entry, dict):
                slots.update(self._parse_day(entry))
        return self._assemble_week(slots)

    def _parse_day(self, entry: dict) -> dict[tuple[int, int], HourBusyness]:
        day_int = _as_int((entry.get("day_info") or {}).get("day_int"))
        raw = entry.get("day_raw")
        if day_int is None or not 0 <= day_int <= 6 or not isinstance(raw, list):
            return {}
        parsed = {}
        for index, value in enumerate(raw[:24]):
            hour = (DAY_START_HOUR + index) % 24
            # Hours past midnight belong to the next calendar day, which is how
            # Google buckets them too. Without this both sources disagree by a day.
            weekday = day_int if hour >= DAY_START_HOUR else (day_int + 1) % 7
            parsed[(weekday, hour)] = HourBusyness(hour=hour, score=_clamp(value))
        return parsed

    @staticmethod
    def _assemble_week(slots: dict[tuple[int, int], HourBusyness]) -> list[DayBusyness]:
        week = empty_week()
        for day in week:
            day.hours = [
                slots.get((int(day.weekday), hour), HourBusyness(hour=hour)) for hour in range(24)
            ]
        return [week[Weekday(index)] for index in range(7)]

    def _enrich_venue(self, venue: Venue, info: object) -> Venue:
        """Replace the user's typing with what BestTime's geocoder resolved."""
        if not isinstance(info, dict):
            return venue
        return venue.model_copy(
            update={
                "provider_venue_id": str(info.get("venue_id") or venue.provider_venue_id),
                "name": str(info.get("venue_name") or venue.name),
                "address": info.get("venue_address") or venue.address,
                "latitude": info.get("venue_lat"),
                "longitude": info.get("venue_lon"),
            }
        )

    def _build_notes(self) -> list[str]:
        return [
            self._note("note_share_of_peak"),
            self._note("note_panel_origin"),
            self._note("note_day_starts_at_six"),
        ]


def _clamp(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return max(0, min(100, int(round(value))))


def _as_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return int(value)
