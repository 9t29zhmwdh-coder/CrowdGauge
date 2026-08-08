"""FastAPI application: local web interface plus a small JSON API.

The server binds to localhost by default and holds no authentication of its own,
because it is a single user tool. It also sends no CORS headers, so a random
website cannot make a browser spend the user's provider credits.
"""

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from crowdgauge import __version__
from crowdgauge.config import KNOWN_PROVIDERS, Settings, load_settings
from crowdgauge.errors import (
    BusynessUnavailable,
    CrowdGaugeError,
    ProviderNotConfigured,
    UpstreamError,
    VenueNotFound,
)
from crowdgauge.providers.registry import provider_status
from crowdgauge.service import LookupService, busiest_hours, day_summary, quietest_hours
from crowdgauge.texts import DEFAULT_LANGUAGE, normalise_language

STATIC_DIR = Path(__file__).parent / "static"

# Which HTTP status each domain error maps to. Upstream failures are gateway
# errors, missing credentials are a server configuration problem.
_STATUS_BY_ERROR = {
    VenueNotFound: 404,
    BusynessUnavailable: 404,
    ProviderNotConfigured: 503,
    UpstreamError: 502,
}


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application. Tests inject their own settings here."""
    resolved = settings or load_settings()
    service = LookupService(resolved)

    app = FastAPI(
        title="CrowdGauge",
        version=__version__,
        description="Venue busyness lookup across swappable footfall data providers",
    )
    app.state.settings = resolved
    app.state.service = service
    _register_routes(app)
    _register_error_handler(app)
    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


def get_service(request: Request) -> LookupService:
    return request.app.state.service


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def _register_routes(app: FastAPI) -> None:
    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        page = STATIC_DIR / "index.html"
        if not page.is_file():
            raise HTTPException(status_code=404, detail="Interface files are missing.")
        return FileResponse(page)

    @app.get("/api/health")
    async def health(settings: Settings = Depends(get_settings)) -> dict[str, object]:
        return {
            "status": "ok",
            "version": __version__,
            "active_provider": settings.configured_providers()[0],
        }

    @app.get("/api/providers")
    async def providers(
        lang: str = Query(default=DEFAULT_LANGUAGE, max_length=10),
        settings: Settings = Depends(get_settings),
    ) -> dict[str, object]:
        return {
            "providers": provider_status(settings, normalise_language(lang)),
            "default": settings.provider,
        }

    @app.get("/api/search")
    async def search(
        q: str = Query(min_length=2, max_length=200),
        provider: str | None = Query(default=None),
        limit: int = Query(default=8, ge=1, le=20),
        lang: str = Query(default=DEFAULT_LANGUAGE, max_length=10),
        service: LookupService = Depends(get_service),
    ) -> dict[str, object]:
        used, venues = await service.search(
            q, _validated_provider(provider), limit=limit, language=normalise_language(lang)
        )
        return {"provider": used.name, "venues": [venue.model_dump() for venue in venues]}

    @app.get("/api/busyness")
    async def busyness(
        q: str = Query(min_length=2, max_length=200),
        provider: str | None = Query(default=None),
        lang: str = Query(default=DEFAULT_LANGUAGE, max_length=10),
        service: LookupService = Depends(get_service),
    ) -> dict[str, object]:
        report = await service.report_for_query(
            q, _validated_provider(provider), language=normalise_language(lang)
        )
        return _serialise(report)

    @app.get("/api/venues/{venue_id}/busyness")
    async def venue_busyness(
        venue_id: str,
        name: str = Query(min_length=1, max_length=200),
        address: str | None = Query(default=None, max_length=300),
        provider: str | None = Query(default=None),
        lang: str = Query(default=DEFAULT_LANGUAGE, max_length=10),
        service: LookupService = Depends(get_service),
    ) -> dict[str, object]:
        report = await service.report_for_venue_id(
            venue_id,
            name,
            address,
            _validated_provider(provider),
            language=normalise_language(lang),
        )
        return _serialise(report)


def _register_error_handler(app: FastAPI) -> None:
    @app.exception_handler(CrowdGaugeError)
    async def handle_domain_error(_: Request, exc: CrowdGaugeError) -> JSONResponse:
        status = next(
            (code for error, code in _STATUS_BY_ERROR.items() if isinstance(exc, error)), 500
        )
        return JSONResponse(
            status_code=status,
            content={"error": type(exc).__name__, "detail": str(exc)},
        )


def _validated_provider(provider: str | None) -> str | None:
    """Reject unknown provider names before they reach the registry."""
    if provider is None or not provider.strip():
        return None
    choice = provider.strip().lower()
    if choice not in (*KNOWN_PROVIDERS, "auto"):
        raise HTTPException(status_code=400, detail=f"Unknown provider '{choice}'.")
    return choice


def _serialise(report) -> dict[str, object]:
    """Add the derived figures the interface shows next to the raw week."""
    return {
        "report": report.model_dump(mode="json"),
        "insights": {
            "has_forecast": report.has_forecast,
            "busiest": busiest_hours(report),
            "quietest": quietest_hours(report),
            "days": [day_summary(day) for day in report.days],
        },
    }


app = create_app()
