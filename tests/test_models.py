"""Tests for the shared data model."""

import pytest
from pydantic import ValidationError

from crowdgauge.models import DayBusyness, HourBusyness, Weekday, empty_week


def test_empty_week_has_seven_days_of_24_hours():
    week = empty_week()
    assert len(week) == 7
    assert [int(day.weekday) for day in week] == list(range(7))
    assert all(len(day.hours) == 24 for day in week)
    assert all(not slot.has_data for day in week for slot in day.hours)


def test_hours_are_sorted_regardless_of_input_order():
    day = DayBusyness(
        weekday=Weekday.FRIDAY,
        hours=[HourBusyness(hour=9, score=50), HourBusyness(hour=3, score=10)],
    )
    assert [slot.hour for slot in day.hours] == [3, 9]


def test_peak_returns_the_highest_scored_slot():
    day = DayBusyness(
        weekday=Weekday.MONDAY,
        hours=[
            HourBusyness(hour=8, score=30),
            HourBusyness(hour=12, score=88),
            HourBusyness(hour=20, score=None),
        ],
    )
    peak = day.peak
    assert peak is not None
    assert (peak.hour, peak.score) == (12, 88)


def test_peak_is_none_when_no_hour_has_data():
    day = DayBusyness(weekday=Weekday.SUNDAY, hours=[HourBusyness(hour=hour) for hour in range(24)])
    assert day.peak is None


def test_zero_is_data_and_none_is_not():
    assert HourBusyness(hour=4, score=0).has_data is True
    assert HourBusyness(hour=4, score=None).has_data is False


@pytest.mark.parametrize("score", [-1, 101])
def test_scores_outside_the_documented_range_are_rejected(score):
    with pytest.raises(ValidationError):
        HourBusyness(hour=1, score=score)


@pytest.mark.parametrize("hour", [-1, 24])
def test_hours_outside_a_day_are_rejected(hour):
    with pytest.raises(ValidationError):
        HourBusyness(hour=hour)
