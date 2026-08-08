"""Provider independent data model.

Every provider normalises its own response shape into these types, so the API
and the frontend never learn which upstream service answered. Busyness is
always expressed the way Google and BestTime both express it: a percentage of
that venue's own peak, where 100 means as busy as this place ever gets. It is
not a head count and cannot be converted into one.
"""

from datetime import UTC, datetime
from enum import IntEnum

from pydantic import BaseModel, Field, field_validator

WEEKDAY_KEYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


class Weekday(IntEnum):
    """Weekday index matching datetime.weekday(), Monday is zero."""

    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


class HourBusyness(BaseModel):
    """Busyness for a single hour slot in the venue's local time."""

    hour: int = Field(ge=0, le=23)
    score: int | None = Field(default=None, ge=0, le=100)
    label: str | None = None

    @property
    def has_data(self) -> bool:
        return self.score is not None


class DayBusyness(BaseModel):
    """A full local day of hour slots, sorted by hour."""

    weekday: Weekday
    hours: list[HourBusyness] = Field(default_factory=list)

    @field_validator("hours")
    @classmethod
    def sort_hours(cls, hours: list[HourBusyness]) -> list[HourBusyness]:
        return sorted(hours, key=lambda slot: slot.hour)

    @property
    def peak(self) -> HourBusyness | None:
        scored = [slot for slot in self.hours if slot.has_data]
        return max(scored, key=lambda slot: slot.score or 0) if scored else None


class LiveBusyness(BaseModel):
    """Current busyness relative to what is typical for this hour."""

    score: int | None = Field(default=None, ge=0, le=100)
    delta_to_typical: int | None = None
    label: str | None = None
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Venue(BaseModel):
    """A place as the answering provider identifies it."""

    provider: str
    provider_venue_id: str
    name: str
    address: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class BusynessReport(BaseModel):
    """Everything CrowdGauge knows about one venue after one lookup."""

    venue: Venue
    provider: str
    provider_label: str
    attribution: str
    days: list[DayBusyness] = Field(default_factory=list)
    live: LiveBusyness | None = None
    typical_visit_duration: str | None = None
    notes: list[str] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def has_forecast(self) -> bool:
        return any(slot.has_data for day in self.days for slot in day.hours)


def empty_week() -> list[DayBusyness]:
    """Return seven days of 24 empty hour slots, used as a parsing baseline."""
    return [
        DayBusyness(weekday=Weekday(index), hours=[HourBusyness(hour=hour) for hour in range(24)])
        for index in range(7)
    ]
