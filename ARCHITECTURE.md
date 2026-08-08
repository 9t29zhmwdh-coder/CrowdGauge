# Architecture

CrowdGauge is a thin application around one idea: **no layer above the adapters knows which data
source answered.** That is what makes the sources interchangeable and what keeps a future provider
from rippling through the codebase.

## Layers

```
crowdgauge/
├── models.py          normalised data model, the contract between all layers
├── errors.py          domain errors, mapped to HTTP status codes in app.py
├── config.py          environment configuration, keys as SecretStr
├── cache.py           in-memory TTL cache
├── providers/
│   ├── base.py        abstract BusynessProvider, shared HTTP and error handling
│   ├── serpapi.py     Google Maps popular times, relayed by SerpApi
│   ├── besttime.py    BestTime.app footfall panel
│   ├── opendata_ch.py Swiss municipal counting stations, no API key
│   ├── demo.py        synthetic curves, no network access
│   └── registry.py    provider selection, the only place that knows the concrete classes
├── service.py         orchestration, caching, derived figures
├── app.py             FastAPI routes and error mapping
├── cli.py             terminal interface
└── static/            interface: index.html, styles.css, app.js, i18n.js
```

Dependencies point in one direction only: `app.py` and `cli.py` depend on `service.py`, which
depends on `providers/`, which depends on `models.py`. Nothing points back up.

## The normalised model

Every provider returns a `BusynessReport`, no matter how its own payload looks:

- `days`: exactly seven `DayBusyness`, each with exactly 24 `HourBusyness` slots
- `score`: 0 to 100, a share of that venue's own peak, or `None` where the source has no data
- `count`: actual people per hour, only where the source measures rather than estimates
- `live`: optional current value plus the delta against what is typical for that hour
- `notes`: provider specific caveats, shown verbatim in the interface

Sources differ in what they can express, and the model has to carry that difference rather than
flatten it. Google and BestTime publish only a relative figure; a counting station publishes people.
`count` therefore exists alongside `score` instead of replacing it, and every consumer has to handle
its absence.

The distinction between `score = 0` and `score = None` matters. Zero means measured and empty,
`None` means the source said nothing. The interface draws them differently, and the recommendation
of quiet hours skips both.

## Adding a provider

1. Write an adapter in `providers/` that inherits `BusynessProvider` and implements
   `search_venues` and `fetch_report`.
2. Use `self._get_json` or `self._post_json` from the base class, so timeouts, HTTP status codes
   and malformed payloads become `UpstreamError` with a message that carries no credentials.
3. Add the credentials to `config.py` as `SecretStr` and extend `configured_providers`.
4. Add one branch in `registry.py` plus one entry in `provider_status`.
5. Write tests against recorded response shapes with `respx`. This is where the real work sits:
   what the upstream documentation says and what the API actually returns are not always the same.

Nothing else changes. The interface, the API and the CLI pick the new source up automatically.

## Deliberate design decisions

**Forecasts are cached, live values are not.** Providers bill per request, and a weekly curve does
not change between two lookups a minute apart. A live value that is a minute old is worthless, so it
bypasses the cache entirely.

**Calendar day semantics across all sources.** BestTime reports a venue day starting at 06:00, so
its `day_raw[19]` is 01:00 of the *following* day. The adapter shifts those hours onto the next
calendar day, which is how Google buckets them. Without that shift the two sources would disagree by
a full day for anything with a nightlife pattern.

**No CORS headers.** The server is a single user tool on localhost. Without CORS a random website
cannot make the browser spend the user's provider credits.

**Errors are typed, not stringly.** `BusynessUnavailable` (the venue exists but has no data) is a
different case from `VenueNotFound` and from `UpstreamError`. The interface says something useful
for each one instead of showing a generic failure.

## Testing approach

Adapters are tested against recorded response shapes rather than the live APIs, because live tests
would cost credits, need secrets in CI and fail for reasons unrelated to the code. The consequence
is honest to state: the tests prove the parsing logic, they do not prove that the upstream schema is
still what the documentation describes. See `ROADMAP.md` for the contract test that closes that gap.
