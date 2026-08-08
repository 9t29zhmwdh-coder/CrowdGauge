# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-08-08

### Added

- Provider abstraction (`BusynessProvider`) with three adapters: SerpApi for Google Maps popular
  times, BestTime.app for an independent footfall panel, and a synthetic demo source that runs
  without any API key
- Normalised data model where every source returns seven days of 24 hourly slots, scored as a share
  of the venue's own peak, with a measured zero distinct from missing data
- FastAPI web interface with a weekly heatmap, live busyness tile, quietest and busiest slots, a
  per day bar chart, and a table view of the same numbers
- JSON API: `/api/health`, `/api/providers`, `/api/search`, `/api/busyness`,
  `/api/venues/{id}/busyness`
- CLI mode with sparkline output (`crowdgauge lookup`, `crowdgauge providers`, `crowdgauge serve`)
- Interface in English and German, following the browser language, with the choice remembered
- Deep links: `/?q=Venue,City&provider=serpapi` runs the lookup on page load
- In-memory TTL cache for forecasts, while live values are always fetched fresh, which keeps
  provider credit use predictable

### Security

- API keys held as `SecretStr`, never written to disk by the application
- Error messages generated from HTTP status codes only, so an upstream response can never echo a key
  back to the user, covered by a test
- Server binds to localhost and sends no CORS headers
- CI pins every GitHub Action to a commit SHA and runs `pip-audit` on each pull request

[0.1.0]: https://github.com/9t29zhmwdh-coder/CrowdGauge/releases/tag/v0.1.0
