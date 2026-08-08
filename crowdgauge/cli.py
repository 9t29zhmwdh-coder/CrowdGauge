"""Command line entry point: serve the web app or query a venue in the terminal."""

import asyncio

import typer
import uvicorn
from rich.console import Console
from rich.table import Table

from crowdgauge import __version__
from crowdgauge.config import load_settings
from crowdgauge.errors import CrowdGaugeError
from crowdgauge.models import BusynessReport
from crowdgauge.providers.registry import provider_status
from crowdgauge.service import LookupService, quietest_hours

app = typer.Typer(help="Venue busyness lookup across swappable footfall providers.")
console = Console()

WEEKDAY_LABELS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
# Eight bar glyphs give a readable sparkline without needing colour support. The
# lowest glyph is a visible bar, not a space, so a measured zero stays
# distinguishable from an hour with no data at all.
_BARS = "▁▂▃▄▅▆▇█"


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
    query: str = typer.Argument(help="Venue, ideally as 'name, city'."),
    provider: str | None = typer.Option(None, help="Force a provider: serpapi, besttime, demo."),
    lang: str = typer.Option("en", help="Language for source notes: en or de."),
) -> None:
    """Print the weekly busyness of one venue."""
    settings = load_settings()
    service = LookupService(settings)
    try:
        report = asyncio.run(service.report_for_query(query, provider, language=lang))
    except CrowdGaugeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    _render_report(report)


@app.command()
def providers() -> None:
    """Show which data sources are configured."""
    table = Table(title="Data providers")
    table.add_column("Provider")
    table.add_column("Configured")
    table.add_column("Source")
    for entry in provider_status(load_settings()):
        mark = "[green]yes[/green]" if entry["configured"] else "[yellow]no[/yellow]"
        table.add_row(str(entry["label"]), mark, str(entry["source"]))
    console.print(table)


def _render_report(report: BusynessReport) -> None:
    console.print(f"\n[bold]{report.venue.name}[/bold]")
    if report.venue.address:
        console.print(report.venue.address)
    console.print(f"[dim]{report.attribution}[/dim]\n")
    _render_live(report)
    _render_week(report)
    _render_quiet(report)
    for note in report.notes:
        console.print(f"[dim]note: {note}[/dim]")


def _render_live(report: BusynessReport) -> None:
    if report.live is None or report.live.score is None:
        return
    delta = report.live.delta_to_typical
    trend = "" if delta is None else f" ({delta:+d} vs typical)"
    console.print(f"Right now: [bold]{report.live.score}%[/bold] of peak{trend}")
    if report.live.label:
        console.print(f"[dim]{report.live.label}[/dim]")
    console.print()


def _render_week(report: BusynessReport) -> None:
    table = Table(title="Busyness as share of this venue's peak")
    table.add_column("Day")
    table.add_column("00 to 23")
    table.add_column("Peak", justify="right")
    for day in report.days:
        peak = day.peak
        peak_text = f"{peak.score}% at {peak.hour:02d}:00" if peak else "no data"
        table.add_row(WEEKDAY_LABELS[int(day.weekday)], _sparkline(day), peak_text)
    console.print(table)


def _sparkline(day) -> str:
    return "".join(
        "·" if slot.score is None else _BARS[min(7, (slot.score * 8) // 100)] for slot in day.hours
    )


def _render_quiet(report: BusynessReport) -> None:
    quiet = quietest_hours(report)
    if not quiet:
        return
    slots = ", ".join(
        f"{WEEKDAY_LABELS[entry['weekday']]} {entry['hour']:02d}:00 ({entry['score']}%)"
        for entry in quiet
    )
    console.print(f"\nQuietest open slots: {slots}\n")


if __name__ == "__main__":
    app()
