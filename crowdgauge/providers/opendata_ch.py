"""Swiss open data adapter: public pedestrian counting stations.

This is the only source in CrowdGauge that needs no account and no API key, and
the only one that reports actual head counts rather than a relative figure. The
cities publish sensor readings per hour under an open licence through
Opendatasoft, so the whole weekly curve comes back from a single aggregation
query.

What it measures is different from the other providers, and the difference
matters: a counting station records people passing a street cross section, not
how full a venue is. It answers "how busy is this spot" rather than "how busy
is this restaurant".
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from crowdgauge.errors import BusynessUnavailable, UpstreamError, VenueNotFound
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

# Weeks of history the weekly average is built from. Long enough to smooth out
# a rained out Saturday, short enough to still reflect the current season.
HISTORY_WEEKS = 10

# A counting station publishes in batches, so its newest reading is usually a
# few hours old. Beyond this age it is history, not a live value.
LIVE_MAX_AGE_HOURS = 6

# Opendatasoft caps a page at 100 rows, and a full week needs 168 groups.
_PAGE_SIZE = 100
_WEEK_GROUPS = 168


@dataclass(frozen=True)
class CityCatalogue:
    """One city's Opendatasoft dataset and the column names it uses."""

    key: str
    label: str
    base_url: str
    dataset: str
    site_field: str
    weekday_field: str
    hour_field: str
    value_field: str
    timestamp_field: str
    pedestrian_filter: str
    attribution: str


CITIES: tuple[CityCatalogue, ...] = (
    CityCatalogue(
        key="basel",
        label="Basel",
        base_url="https://data.bs.ch/api/explore/v2.1",
        dataset="100013",
        site_field="sitename",
        weekday_field="weekday",
        hour_field="hourfrom",
        value_field="total",
        timestamp_field="datetimefrom",
        pedestrian_filter="traffictype='Fussgänger'",
        attribution="Open Government Data, Kanton Basel-Stadt",
    ),
)


class OpenDataCHProvider(BusynessProvider):
    """Reads Swiss municipal pedestrian counters, no API key required."""

    name = "opendata_ch"
    display_name = "Swiss open data (counting stations)"
    attribution_key = "attribution_opendata_ch"
    supports_live = True

    async def search_venues(self, query: str, limit: int = DEFAULT_SEARCH_LIMIT) -> list[Venue]:
        term = normalise_query(query)
        venues: list[Venue] = []
        failures: list[UpstreamError] = []
        for city in CITIES:
            try:
                venues.extend(await self._search_city(city, term, limit))
            except UpstreamError as exc:
                # One city being down must not fail a multi city search, but if
                # every city fails, that is an outage and not an empty result.
                failures.append(exc)
        if not venues and failures:
            raise failures[0]
        if not venues:
            raise VenueNotFound(
                f"No Swiss counting station matches '{term}'. "
                f"Covered so far: {', '.join(city.label for city in CITIES)}."
            )
        return venues[:limit]

    async def fetch_report(self, venue: Venue) -> BusynessReport:
        city = self._city_for(venue.provider_venue_id)
        site = _site_from_id(venue.provider_venue_id)
        rows = await self._fetch_week(city, site)
        if not rows:
            raise BusynessUnavailable(
                f"'{venue.name}' has no readings in the last {HISTORY_WEEKS} weeks."
            )
        days, peak = self._build_week(rows)
        latest = await self._latest_reading(city, site)
        return BusynessReport(
            venue=venue,
            provider=self.name,
            provider_label=f"{self.display_name}, {city.label}",
            attribution=f"{self._note('attribution_opendata_ch')}: {city.attribution}",
            days=days,
            live=self._to_live(latest, peak),
            notes=self._build_notes(city, latest),
        )

    async def _search_city(self, city: CityCatalogue, term: str, limit: int) -> list[Venue]:
        """List counting station names matching the term.

        Only the name is selected. Coordinates are not part of the grouped
        result, and the interface shows no map, so fetching them would cost a
        second request for nothing.
        """
        params = {
            "select": city.site_field,
            "group_by": city.site_field,
            # search() matches substrings; ODSQL's "like" needs an exact value.
            "where": f"{city.pedestrian_filter} and search({city.site_field}, {_quote(term)})",
            "limit": str(min(limit, _PAGE_SIZE)),
        }
        payload = await self._get_json(
            f"{city.base_url}/catalog/datasets/{city.dataset}/records", params
        )
        return [
            self._to_venue(city, row)
            for row in payload.get("results", [])
            if row.get(city.site_field)
        ]

    def _to_venue(self, city: CityCatalogue, row: dict) -> Venue:
        site = str(row[city.site_field])
        return Venue(
            provider=self.name,
            provider_venue_id=f"{city.key}:{site}",
            name=site,
            address=city.label,
        )

    async def _fetch_week(self, city: CityCatalogue, site: str) -> list[dict]:
        """Average each weekday and hour over the history window, server side."""
        since = (datetime.now(UTC) - timedelta(weeks=HISTORY_WEEKS)).date().isoformat()
        rows: list[dict] = []
        for offset in range(0, _WEEK_GROUPS, _PAGE_SIZE):
            selection = (
                f"{city.weekday_field}, {city.hour_field}, avg({city.value_field}) as mean_value"
            )
            params = {
                "select": selection,
                "group_by": f"{city.weekday_field}, {city.hour_field}",
                "where": (
                    f"{city.pedestrian_filter} and {city.site_field}={_quote(site)} "
                    f"and {city.timestamp_field} > date'{since}'"
                ),
                "limit": str(_PAGE_SIZE),
                "offset": str(offset),
            }
            payload = await self._get_json(
                f"{city.base_url}/catalog/datasets/{city.dataset}/records", params
            )
            page = payload.get("results", [])
            rows.extend(page)
            if len(page) < _PAGE_SIZE:
                break
        return rows

    def _build_week(self, rows: list[dict]) -> tuple[list[DayBusyness], float]:
        """Turn the aggregated rows into a week, scored against the weekly peak."""
        counts = _collect_counts(rows)
        peak = max(counts.values(), default=0.0)
        week = empty_week()
        for day in week:
            day.hours = [
                _slot(hour, counts.get((int(day.weekday), hour)), peak) for hour in range(24)
            ]
        return [week[Weekday(index)] for index in range(7)], peak

    async def _latest_reading(
        self, city: CityCatalogue, site: str
    ) -> tuple[datetime, float] | None:
        """Newest published hour for this station, whatever its age."""
        params = {
            "select": f"{city.timestamp_field}, sum({city.value_field}) as hour_value",
            "group_by": city.timestamp_field,
            "where": f"{city.pedestrian_filter} and {city.site_field}={_quote(site)}",
            "order_by": f"{city.timestamp_field} desc",
            "limit": "1",
        }
        try:
            payload = await self._get_json(
                f"{city.base_url}/catalog/datasets/{city.dataset}/records", params
            )
        except UpstreamError:
            return None
        rows = payload.get("results") or []
        if not rows:
            return None
        measured_at = _parse_timestamp(rows[0].get(city.timestamp_field))
        value = _as_float(rows[0].get("hour_value"))
        return (measured_at, value) if measured_at and value is not None else None

    def _to_live(self, latest: tuple[datetime, float] | None, peak: float) -> LiveBusyness | None:
        """Only count a reading as live while it is still recent."""
        if latest is None or peak <= 0:
            return None
        measured_at, value = latest
        if datetime.now(UTC) - measured_at > timedelta(hours=LIVE_MAX_AGE_HOURS):
            return None
        return LiveBusyness(
            score=_clamp_percent(value / peak * 100),
            count=int(round(value)),
            measured_at=measured_at,
            label=self._note("live_measured_people", count=str(int(round(value)))),
        )

    def _city_for(self, venue_id: str) -> CityCatalogue:
        key = venue_id.split(":", 1)[0]
        city = next((entry for entry in CITIES if entry.key == key), None)
        if city is None:
            raise VenueNotFound(f"Unknown counting station reference '{venue_id}'.")
        return city

    def _build_notes(self, city: CityCatalogue, latest: tuple[datetime, float] | None) -> list[str]:
        notes = [
            self._note("note_counting_station"),
            self._note("note_open_licence", city=city.attribution),
            self._note("note_history_window", weeks=str(HISTORY_WEEKS)),
        ]
        # A missing live value has two very different causes. Saying which one
        # applies is the difference between "broken" and "published in batches".
        if latest is None:
            notes.append(self._note("note_no_reading"))
        elif datetime.now(UTC) - latest[0] > timedelta(hours=LIVE_MAX_AGE_HOURS):
            notes.append(self._note("note_reading_too_old", timestamp=_format_local(latest[0])))
        return notes


def _collect_counts(rows: list[dict]) -> dict[tuple[int, int], float]:
    """Index the aggregated rows by weekday and hour, ignoring unusable ones."""
    counts: dict[tuple[int, int], float] = {}
    for row in rows:
        weekday = _as_int(row.get("weekday"))
        hour = _as_int(row.get("hourfrom"))
        value = _as_float(row.get("mean_value"))
        if weekday is None or hour is None or value is None:
            continue
        if 0 <= weekday <= 6 and 0 <= hour <= 23:
            counts[(weekday, hour)] = value
    return counts


def _slot(hour: int, value: float | None, peak: float) -> HourBusyness:
    if value is None or peak <= 0:
        return HourBusyness(hour=hour)
    return HourBusyness(
        hour=hour, score=_clamp_percent(value / peak * 100), count=int(round(value))
    )


def _quote(value: str) -> str:
    """Quote a literal for ODSQL, escaping the quote character.

    The station name reaches this function from a client supplied venue id, so
    it is untrusted input going into a query language.
    """
    return "'" + value.replace("\\", "").replace("'", "''") + "'"


def _site_from_id(venue_id: str) -> str:
    _, _, site = venue_id.partition(":")
    return site or venue_id


def _clamp_percent(value: float) -> int:
    return max(0, min(100, int(round(value))))


def _as_float(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _as_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return int(value)


def _format_local(moment: datetime) -> str:
    """Readable timestamp for a note, in the reader's own clock."""
    return moment.astimezone().strftime("%d.%m.%Y %H:%M")


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
