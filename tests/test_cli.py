"""Tests for the terminal interface and the provider registry."""

import pytest
from typer.testing import CliRunner

from crowdgauge.cli import _sparkline, app, detect_language
from crowdgauge.config import PROVIDER_DEMO, PROVIDER_OPENDATA, Settings
from crowdgauge.errors import ProviderNotConfigured
from crowdgauge.models import DayBusyness, HourBusyness, Weekday
from crowdgauge.providers.registry import build_provider

runner = CliRunner()


def test_providers_command_lists_every_source():
    result = runner.invoke(app, ["providers", "--lang", "en"])
    assert result.exit_code == 0
    assert "BestTime" in result.stdout
    assert "Demo" in result.stdout
    assert "Open data" in result.stdout


def test_cli_output_is_fully_translated(monkeypatch):
    """A German run must not mix English table headers into the output."""
    monkeypatch.setenv("CROWDGAUGE_PROVIDER", PROVIDER_DEMO)
    result = runner.invoke(app, ["lookup", "Testcafe", "--lang", "de"])
    assert result.exit_code == 0
    assert "Ruhigste offene Zeiten" in result.stdout
    assert "Quietest" not in result.stdout
    assert "Busyness as share" not in result.stdout


def test_cli_language_follows_the_shell_environment(monkeypatch):
    monkeypatch.setenv("LANG", "de_CH.UTF-8")
    monkeypatch.delenv("CROWDGAUGE_LANG", raising=False)
    assert detect_language() == "de"


def test_unsupported_shell_language_falls_back_to_english(monkeypatch):
    monkeypatch.setenv("CROWDGAUGE_LANG", "fr_CH.UTF-8")
    assert detect_language() == "en"


def test_lookup_prints_a_week(monkeypatch):
    monkeypatch.setenv("CROWDGAUGE_PROVIDER", PROVIDER_DEMO)
    result = runner.invoke(app, ["lookup", "Test Cafe, Aarau", "--lang", "en"])
    assert result.exit_code == 0
    assert "Test Cafe" in result.stdout
    assert "Quietest open slots" in result.stdout


def test_lookup_exits_non_zero_when_the_provider_is_unconfigured(monkeypatch):
    monkeypatch.setenv("CROWDGAUGE_PROVIDER", "serpapi")
    monkeypatch.delenv("CROWDGAUGE_SERPAPI_KEY", raising=False)
    result = runner.invoke(app, ["lookup", "Test Cafe"])
    assert result.exit_code == 1


def test_sparkline_distinguishes_a_measured_zero_from_missing_data():
    day = DayBusyness(
        weekday=Weekday.MONDAY,
        hours=[
            HourBusyness(hour=0, score=0),
            HourBusyness(hour=1, score=100),
            HourBusyness(hour=2, score=None),
        ],
    )
    line = _sparkline(day)
    assert line[0] == "▁"
    assert line[1] == "█"
    assert line[2] == "·"


def test_auto_prefers_the_keyless_open_data_source():
    """Without credentials, real measurements beat synthetic curves."""
    provider = build_provider(Settings(provider="auto"))
    assert provider.name == PROVIDER_OPENDATA


def test_demo_remains_the_last_resort():
    assert Settings(provider="auto").configured_providers()[-1] == PROVIDER_DEMO


def test_unknown_provider_name_is_rejected():
    with pytest.raises(ProviderNotConfigured):
        build_provider(Settings(), requested="rumour-mill")


def test_requesting_besttime_without_keys_names_both_variables():
    with pytest.raises(ProviderNotConfigured) as excinfo:
        build_provider(Settings(), requested="besttime")
    assert "CROWDGAUGE_BESTTIME_PRIVATE_KEY" in str(excinfo.value)
    assert "CROWDGAUGE_BESTTIME_PUBLIC_KEY" in str(excinfo.value)
