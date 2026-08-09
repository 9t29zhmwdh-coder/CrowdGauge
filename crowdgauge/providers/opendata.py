"""Open data adapter: public pedestrian counting stations, no API key.

Cities across several countries publish their pedestrian counter readings under
an open licence on Opendatasoft portals. They all speak the same query language,
so one adapter covers all of them and a new city is a row in `CITIES` rather
than new code. This is also the only source in CrowdGauge that reports actual
head counts instead of a relative figure.

What it measures differs from the commercial providers, and the difference
matters: a counting station records people passing a street cross section, not
how full a venue is. It answers "how busy is this spot" rather than "how busy is
this restaurant".

Portals disagree on how they express time. Some ship ready made weekday and hour
columns, others only a timestamp, so each city declares an ODSQL expression for
both and the adapter never assumes a schema.
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

# A counting station publishes in batches, so its newest reading is often hours
# or days old. Beyond this age it is history, not a live value.
LIVE_MAX_AGE_HOURS = 6

# Opendatasoft caps a page at 100 rows, and a full week needs 168 groups.
_PAGE_SIZE = 100
_WEEK_GROUPS = 168

# Federation host, which proxies every public Opendatasoft portal. Using it
# keeps one base URL for cities that have no reachable portal of their own.
FEDERATION = "https://data.opendatasoft.com/api/explore/v2.1"


@dataclass(frozen=True)
class CityCatalogue:
    """One city's dataset, plus how that dataset expresses time and place."""

    key: str
    label: str
    country: str
    base_url: str
    dataset: str
    site_field: str
    value_field: str
    timestamp_field: str
    weekday_expr: str
    """ODSQL expression yielding the weekday, either a column or date_format()."""
    weekday_base: int
    """1 when the expression counts Monday as 1, 0 when Monday is 0."""
    hour_expr: str
    extra_filter: str
    attribution: str

    def records_url(self) -> str:
        return f"{self.base_url}/catalog/datasets/{self.dataset}/records"


CITIES: tuple[CityCatalogue, ...] = (
    CityCatalogue(
        key="basel",
        label="Basel",
        country="CH",
        base_url="https://data.bs.ch/api/explore/v2.1",
        dataset="100013",
        site_field="sitename",
        value_field="total",
        timestamp_field="datetimefrom",
        weekday_expr="weekday",
        weekday_base=0,
        hour_expr="hourfrom",
        extra_filter="traffictype='Fussgänger'",
        attribution="Open Government Data, Kanton Basel-Stadt",
    ),
    # Dortmund publishes one dataset per year AND renames its columns between
    # them: the 2025 edition calls them standort / messzeitpunkt /
    # passantenaufkommen_pro_standort, the 2026 edition name /
    # zeitpunkt_measured_at / zeitpunkt_total_count. A year placeholder would
    # therefore only pretend the schema is stable, so the dataset is pinned and
    # the yearly rollover is a tracked task in ROADMAP.md.
    CityCatalogue(
        key="dortmund",
        label="Dortmund",
        country="DE",
        base_url=FEDERATION,
        dataset="passantenaufkommen-fussgangerzone-hellweg-2026@dortmund",
        site_field="name",
        value_field="zeitpunkt_total_count",
        timestamp_field="zeitpunkt_measured_at",
        weekday_expr="wochentag_id",
        weekday_base=1,
        hour_expr="stunde",
        extra_filter="",
        attribution="Stadt Dortmund, Open Data",
    ),
    CityCatalogue(
        key="melbourne",
        label="Melbourne",
        country="AU",
        base_url=FEDERATION,
        dataset="pedestrian-counting-system-monthly-counts-per-hour@melbournetestbed",
        site_field="sensor_name",
        value_field="pedestriancount",
        timestamp_field="sensing_date",
        weekday_expr='date_format(sensing_date, "e")',
        weekday_base=1,
        hour_expr="hourday",
        extra_filter="",
        attribution="City of Melbourne, Pedestrian Counting System",
    ),
)


class OpenDataProvider(BusynessProvider):
    """Reads municipal pedestrian counters from open data portals."""

    name = "opendata"
    display_name = "Open data (counting stations)"
    attribution_key = "attribution_opendata"
    supports_live = True

    async def search_venues(self, query: str, limit: int = DEFAULT_SEARCH_LIMIT) -> list[Venue]:
        term = normalise_query(query)
        venues: list[Venue] = []
        failures: list[UpstreamError] = []
        for city in CITIES:
            try:
                venues.extend(await self._search_city(city, term, limit))
            except UpstreamError as exc:
                # One portal being down must not fail a search across all of
                # them, but if every portal fails, that is an outage rather
                # than an empty result.
                failures.append(exc)
        if not venues and failures:
            raise failures[0]
        if not venues:
            raise VenueNotFound(
                f"No counting station matches '{term}'. Covered so far: {covered_cities()}."
            )
        return venues[:limit]

    async def fetch_report(self, venue: Venue) -> BusynessReport:
        city = self._city_for(venue.provider_venue_id)
        site = _site_from_id(venue.provider_venue_id)
        rows = await self._fetch_week(city, site)
        counts = _collect_counts(rows, city)
        if not counts:
            raise BusynessUnavailable(
                f"'{venue.name}' has no readings in the last {HISTORY_WEEKS} weeks."
            )
        days, peak = _build_week(counts)
        latest = await self._latest_reading(city, site)
        return BusynessReport(
            venue=venue,
            provider=self.name,
            provider_label=f"{self.display_name}, {city.label}",
            attribution=f"{self._note('attribution_opendata')}: {city.attribution}",
            days=days,
            live=self._to_live(latest, peak),
            notes=self._build_notes(city, latest),
        )

    async def _search_city(self, city: CityCatalogue, term: str, limit: int) -> list[Venue]:
        """List station names matching the term.

        search() matches substrings; ODSQL's "like" compares the whole value.
        """
        params = {
            "select": city.site_field,
            "group_by": city.site_field,
            "where": _and(city.extra_filter, f"search({city.site_field}, {_quote(term)})"),
            "limit": str(min(limit, _PAGE_SIZE)),
        }
        payload = await self._get_json(city.records_url(), params)
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
            address=f"{city.label} ({city.country})",
        )

    async def _fetch_week(self, city: CityCatalogue, site: str) -> list[dict]:
        """Average each weekday and hour over the history window, server side."""
        since = (datetime.now(UTC) - timedelta(weeks=HISTORY_WEEKS)).date().isoformat()
        grouping = f"{city.weekday_expr}, {city.hour_expr}"
        where = _and(
            city.extra_filter,
            f"{city.site_field}={_quote(site)}",
            f"{city.timestamp_field} > date'{since}'",
        )
        rows: list[dict] = []
        for offset in range(0, _WEEK_GROUPS, _PAGE_SIZE):
            params = {
                "select": f"{grouping}, avg({city.value_field}) as mean_value",
                "group_by": grouping,
                "where": where,
                "limit": str(_PAGE_SIZE),
                "offset": str(offset),
            }
            page = (await self._get_json(city.records_url(), params)).get("results", [])
            rows.extend(page)
            if len(page) < _PAGE_SIZE:
                break
        return rows

    async def _latest_reading(
        self, city: CityCatalogue, site: str
    ) -> tuple[datetime, float] | None:
        """Newest published hour for this station, whatever its age."""
        params = {
            "select": f"{city.timestamp_field}, sum({city.value_field}) as hour_value",
            "group_by": city.timestamp_field,
            "where": _and(city.extra_filter, f"{city.site_field}={_quote(site)}"),
            "order_by": f"{city.timestamp_field} desc",
            "limit": "1",
        }
        try:
            payload = await self._get_json(city.records_url(), params)
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


def covered_cities() -> str:
    return ", ".join(f"{city.label} ({city.country})" for city in CITIES)


def _collect_counts(rows: list[dict], city: CityCatalogue) -> dict[tuple[int, int], float]:
    """Index the aggregated rows by weekday and hour, ignoring unusable ones."""
    counts: dict[tuple[int, int], float] = {}
    for row in rows:
        weekday = _as_int(_read(row, city.weekday_expr))
        hour = _as_int(_read(row, city.hour_expr))
        value = _as_float(row.get("mean_value"))
        if weekday is None or hour is None or value is None:
            continue
        weekday -= city.weekday_base
        if 0 <= weekday <= 6 and 0 <= hour <= 23:
            counts[(weekday, hour)] = value
    return counts


def _read(row: dict, expression: str) -> object:
    """Read a grouped value, which may be keyed by column name or by expression.

    Opendatasoft ignores the alias on a computed group_by and returns the raw
    expression as the key with its spaces stripped. It also echoes the spaced
    form back as an empty field, so a candidate that exists but is None has to
    be skipped rather than accepted.
    """
    for candidate in (expression, expression.replace(" ", "")):
        value = row.get(candidate)
        if value is not None:
            return value
    return None


def _build_week(counts: dict[tuple[int, int], float]) -> tuple[list[DayBusyness], float]:
    peak = max(counts.values(), default=0.0)
    week = empty_week()
    for day in week:
        day.hours = [_slot(hour, counts.get((int(day.weekday), hour)), peak) for hour in range(24)]
    return [week[Weekday(index)] for index in range(7)], peak


def _slot(hour: int, value: float | None, peak: float) -> HourBusyness:
    if value is None or peak <= 0:
        return HourBusyness(hour=hour)
    return HourBusyness(
        hour=hour, score=_clamp_percent(value / peak * 100), count=int(round(value))
    )


def _and(*clauses: str) -> str:
    """Join the clauses a city actually has, skipping the empty ones."""
    return " and ".join(clause for clause in clauses if clause)


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
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    # Computed group_by values come back as strings, for example the "e"
    # weekday format.
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _as_int(value: object) -> int | None:
    number = _as_float(value)
    return None if number is None else int(number)


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
