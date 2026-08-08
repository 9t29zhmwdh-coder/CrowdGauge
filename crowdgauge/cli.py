"""Command line entry point: serve the web app or query a venue in the terminal."""

import asyncio
import locale
import os

import typer
import uvicorn
from rich.console import Console
from rich.table import Table

from crowdgauge import __version__
from crowdgauge.config import load_settings
from crowdgauge.errors import CrowdGaugeError
from crowdgauge.models import BusynessReport, DayBusyness
from crowdgauge.providers.registry import provider_status
from crowdgauge.service import LookupService, quietest_hours
from crowdgauge.texts import DEFAULT_LANGUAGE, normalise_language, text

app = typer.Typer(help="Venue busyness lookup across swappable footfall providers.")
console = Console()

# Eight bar glyphs give a readable sparkline without needing colour support. The
# lowest glyph is a visible bar, not a space, so a measured zero stays
# distinguishable from an hour with no data at all.
_BARS = "▁▂▃▄▅▆▇█"


def detect_language() -> str:
    """Follow the shell environment, the terminal equivalent of a browser locale."""
    for variable in ("CROWDGAUGE_LANG", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(variable)
        if value:
            return normalise_language(value)
    try:
        return normalise_language(locale.getlocale()[0] or DEFAULT_LANGUAGE)
    except (ValueError, TypeError):
        return DEFAULT_LANGUAGE


@app.command()
def serve(
    host: str | None = typer.Option(None, help="Bind address, defaults to the configured host."),
    port: int | None = typer.Option(None, help="Port, defaults to the configured port."),
) -> None:
    """Start the local web interface."""
    settings = load_settings()
    bind_host = host or settings.host
    bind_port = port or settings.port
    console.print(f"[bold]CrowdGauge {__version__}[/bold] on http://{bind_host}:{bind_port}")
    console.print(f"Active provider: {settings.configured_providers()[0]}")
    uvicorn.run("crowdgauge.app:app", host=bind_host, port=bind_port, log_level="info")


@app.command()
def lookup(
    query: str = typer.Argument(help="Venue or counting station, ideally as 'name, city'."),
    provider: str | None = typer.Option(
        None, help="Force a provider: opendata_ch, serpapi, besttime, demo."
    ),
    lang: str | None = typer.Option(
        None, help="Output language: en or de. Defaults to your shell."
    ),
) -> None:
    """Print the weekly busyness of one place."""
    language = normalise_language(lang) if lang else detect_language()
    service = LookupService(load_settings())
    try:
        report = asyncio.run(service.report_for_query(query, provider, language=language))
    except CrowdGaugeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    _render_report(report, language)


@app.command()
def providers(
    lang: str | None = typer.Option(None, help="Output language: en or de."),
) -> None:
    """Show which data sources are configured."""
    language = normalise_language(lang) if lang else detect_language()
    table = Table(title=text("cli_providers", language))
    table.add_column(text("cli_provider", language))
    table.add_column(text("cli_configured", language))
    table.add_column(text("cli_source", language))
    for entry in provider_status(load_settings(), language):
        mark = (
            f"[green]{text('cli_yes', language)}[/green]"
            if entry["configured"]
            else f"[yellow]{text('cli_no', language)}[/yellow]"
        )
        table.add_row(str(entry["label"]), mark, str(entry["source"]))
    console.print(table)


def _weekday_labels(language: str) -> list[str]:
    return text("cli_weekdays_short", language).split(",")


def _render_report(report: BusynessReport, language: str) -> None:
    console.print(f"\n[bold]{report.venue.name}[/bold]")
    if report.venue.address:
        console.print(report.venue.address)
    console.print(f"[dim]{report.attribution}[/dim]\n")
    _render_live(report, language)
    _render_week(report, language)
    _render_quiet(report, language)
    for note in report.notes:
        console.print(f"[dim]{note}[/dim]")


def _render_live(report: BusynessReport, language: str) -> None:
    if report.live is None or report.live.score is None:
        return
    delta = report.live.delta_to_typical
    trend = "" if delta is None else f" ({delta:+d} {text('cli_vs_typical', language)})"
    label = text("cli_right_now", language)
    console.print(
        f"{label}: [bold]{report.live.score}%[/bold] {text('cli_of_peak', language)}{trend}"
    )
    if report.live.label:
        console.print(f"[dim]{report.live.label}[/dim]")
    console.print()


def _render_week(report: BusynessReport, language: str) -> None:
    labels = _weekday_labels(language)
    table = Table(title=text("cli_week_title", language))
    table.add_column(text("cli_day", language))
    table.add_column(text("cli_hours", language))
    table.add_column(text("cli_peak", language), justify="right")
    for day in report.days:
        table.add_row(labels[int(day.weekday)], _sparkline(day), _peak_text(day, language))
    console.print(table)


def _peak_text(day: DayBusyness, language: str) -> str:
    peak = day.peak
    if peak is None:
        return text("cli_no_data", language)
    figure = f"{peak.score}% {text('cli_at', language)} {peak.hour:02d}:00"
    if peak.count is None:
        return figure
    return f"{figure}, {peak.count} {text('cli_people_per_hour', language)}"


def _sparkline(day: DayBusyness) -> str:
    return "".join(
        "·" if slot.score is None else _BARS[min(7, (slot.score * 8) // 100)] for slot in day.hours
    )


def _render_quiet(report: BusynessReport, language: str) -> None:
    quiet = quietest_hours(report)
    if not quiet:
        return
    labels = _weekday_labels(language)
    slots = ", ".join(
        f"{labels[entry['weekday']]} {entry['hour']:02d}:00 ({entry['score']}%)" for entry in quiet
    )
    console.print(f"\n{text('cli_quietest', language)}: {slots}\n")


if __name__ == "__main__":
    app()
