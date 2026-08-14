# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.2] - 2026-08-14

### Changed

- The CodeQL workflow now matches the setup the other repositories in this portfolio use: the job
  requests only `security-events: write` instead of repeating the read grants the workflow already
  defaults to, which OpenSSF Scorecard counts as excessive token permissions, and the analysis runs
  the `security-extended` query suite rather than the default one

## [0.2.1] - 2026-08-14

### Changed

- CodeQL moved from the repository default setup to a workflow in the repository
  (`.github/workflows/codeql.yml`). Default setup never runs on Dependabot pull requests, so the
  required `Analyze (python)` and `Analyze (actions)` checks were missing there and every Dependabot
  pull request stayed blocked. The workflow keeps the same three languages and the same check names,
  so the branch ruleset is unchanged and stays enforced
- GitHub Actions updated within their pinned SHAs: `actions/checkout` to v7.0.1, `actions/setup-python`
  to v7.0.0, `ossf/scorecard-action` to v2.4.4 and `github/codeql-action` to v4.37.6

## [0.2.0] - 2026-08-08

### Added

- Open data provider (`opendata`): public pedestrian counting stations queried through Opendatasoft,
  no account and no API key. Covered so far: Basel (CH), Dortmund (DE) and Melbourne (AU), all three
  verified against the live portals. The city catalogue is a table, so a further city is a data
  change rather than a code change
- Actual head counts: `HourBusyness.count` and `LiveBusyness.count` carry people per hour where the
  source measures them, shown in the heatmap tooltips, the stat tiles and the live tile
- `measured_at` on live values, because counting stations publish in batches and a reading has to be
  shown with its own timestamp
- The terminal output is translated as well and follows the shell locale by default, so a German run
  no longer mixes English table headers into the result
- The setup notice links to the provider sign up pages, because every source that covers arbitrary
  venues needs an account the user creates themselves

### Changed

- Without a configured key the active source is now `opendata` instead of `demo`: a real
  measurement beats a synthetic curve. The demo provider stays as the last resort
- The weekly subtitle adapts to the source, since "this is not a head count" is wrong for a station
  that counts heads
- Product icon replaces the studio logo in the README header

### Fixed

- A reading older than six hours is no longer presented as a live value, and the interface states
  why the live value is missing instead of leaving it blank

## [0.1.1] - 2026-08-08

### Documentation

- Record in `ROADMAP.md` which hosting options were weighed for a public instance (GitHub Pages,
  scheduled Action, Codespaces, Azure Container Apps) and why the decision is deferred: without an
  authentication story, any public deployment either exposes a paid provider quota or redistributes
  data it is not licensed to serve

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

[0.2.2]: https://github.com/9t29zhmwdh-coder/CrowdGauge/releases/tag/v0.2.2
[0.2.1]: https://github.com/9t29zhmwdh-coder/CrowdGauge/releases/tag/v0.2.1
[0.2.0]: https://github.com/9t29zhmwdh-coder/CrowdGauge/releases/tag/v0.2.0
[0.1.1]: https://github.com/9t29zhmwdh-coder/CrowdGauge/releases/tag/v0.1.1
[0.1.0]: https://github.com/9t29zhmwdh-coder/CrowdGauge/releases/tag/v0.1.0
