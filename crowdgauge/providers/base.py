"""The contract every footfall data source has to satisfy.

A provider does two things: turn a free text location into candidate venues,
and turn one venue into a normalised BusynessReport. Everything above this
layer is provider agnostic, which is what makes Google, BestTime or any future
source interchangeable.
"""

from abc import ABC, abstractmethod

import httpx

from crowdgauge.errors import UpstreamError
from crowdgauge.models import BusynessReport, Venue
from crowdgauge.texts import DEFAULT_LANGUAGE, normalise_language, text

MAX_QUERY_LENGTH = 200
DEFAULT_SEARCH_LIMIT = 8


class BusynessProvider(ABC):
    """Base class for a footfall data source."""

    name: str = "base"
    display_name: str = "Base"
    attribution_key: str = ""
    supports_live: bool = False

    def __init__(self, timeout: float = 20.0, language: str = DEFAULT_LANGUAGE) -> None:
        self._timeout = timeout
        self._language = normalise_language(language)

    @property
    def language(self) -> str:
        return self._language

    @property
    def attribution(self) -> str:
        """Source credit in the interface language."""
        return text(self.attribution_key, self._language) if self.attribution_key else ""

    def _note(self, key: str, **fields: str) -> str:
        return text(key, self._language, **fields)

    @abstractmethod
    async def search_venues(self, query: str, limit: int = DEFAULT_SEARCH_LIMIT) -> list[Venue]:
        """Return candidate venues for a free text location query."""

    @abstractmethod
    async def fetch_report(self, venue: Venue) -> BusynessReport:
        """Return the weekly forecast and, if supported, the live value."""

    async def _get_json(self, url: str, params: dict[str, str]) -> dict:
        """GET a JSON document, translating transport problems into UpstreamError."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            return await self._request_json(client, "GET", url, params=params)

    async def _post_json(self, url: str, params: dict[str, str]) -> dict:
        """POST a query string based JSON call, as BestTime.app expects it."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            return await self._request_json(client, "POST", url, params=params)

    async def _request_json(
        self, client: httpx.AsyncClient, method: str, url: str, **kwargs
    ) -> dict:
        try:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException as exc:
            raise UpstreamError(f"{self.display_name} did not answer in time.") from exc
        except httpx.HTTPStatusError as exc:
            raise UpstreamError(self._status_message(exc.response.status_code)) from exc
        except httpx.HTTPError as exc:
            raise UpstreamError(f"{self.display_name} could not be reached.") from exc
        except ValueError as exc:
            raise UpstreamError(f"{self.display_name} sent a malformed response.") from exc
        if not isinstance(payload, dict):
            raise UpstreamError(f"{self.display_name} sent an unexpected response shape.")
        return payload

    def _status_message(self, status: int) -> str:
        """Map an upstream status to a message that leaks neither key nor payload."""
        if status in (401, 403):
            return f"{self.display_name} rejected the API key."
        if status == 429:
            return f"{self.display_name} rate limit or quota reached."
        if status == 404:
            return f"{self.display_name} has no record for this venue."
        return f"{self.display_name} returned an error (HTTP {status})."


def normalise_query(query: str) -> str:
    """Trim and length limit user input before it reaches an upstream API."""
    cleaned = " ".join(query.split())
    return cleaned[:MAX_QUERY_LENGTH]
