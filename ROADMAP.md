# Roadmap

## Now (0.1.x)

- [x] Provider abstraction with SerpApi, BestTime.app and a synthetic demo source
- [x] Weekly heatmap, live value, quietest and busiest slots
- [x] JSON API, CLI mode, English and German interface
- [ ] Verify both live adapters against real API keys, see the honest limitation below

## Honest limitation right now

The SerpApi and BestTime adapters are written against the providers' published response schemas and
tested against recorded shapes. **They have not yet been run against a live account.** Where the
real payload differs from the documentation, the adapter will need a correction. The demo provider
is fully exercised and the parsing logic is covered by tests, but that is not the same as a verified
integration, and it should not be presented as one.

Closing this means: get a key for each provider, run one real lookup per adapter, record the actual
payload as a test fixture, and fix whatever differs.

## Next

- **Contract tests against recorded live payloads.** Once real responses exist, freeze them as
  fixtures so an upstream schema change fails a test instead of a user's lookup.
- **Foursquare adapter.** Foursquare exposes a popularity signal, though not an hourly curve, and it
  sits behind a premium endpoint. Worth adding once the two hourly sources are verified.
- **Venue picker in the interface.** The API already returns candidates from `/api/search`. The
  interface currently takes the first hit, which is wrong for ambiguous names.
- **Compare two venues side by side.** The obvious question after "how busy is this" is "which of
  these two is quieter right now".
- **Persistent history.** Recording live values over time would show whether a place is trending
  busier, which no provider offers directly.

## Hosting: options weighed, decision deferred

CrowdGauge runs locally. Whether a public instance should exist was assessed on 2026-08-08 and
deliberately left open. Recorded here so the reasoning does not have to be repeated.

| Option | What it would run | Blocker |
|--------|-------------------|---------|
| GitHub Pages | Interface only, demo curves ported to JavaScript | No real data, and a provider key in the client is never acceptable |
| Scheduled GitHub Action | Periodic fetch, results committed as JSON | Redistributing Google Maps content publicly conflicts with the terms that reach me through SerpApi; less of an issue for BestTime |
| Codespaces | The real app with the user's own key | Single user, no continuous availability |
| Azure Container Apps | The real app publicly, key held server side | Needs authentication and a rate limit first, otherwise strangers spend my provider credits |

The recurring constraint is not technical. It is that this tool has no authentication by design, so
any public deployment either exposes someone's paid quota or serves data it is not licensed to
redistribute. A public instance therefore needs an auth story before it needs a hosting platform.

## Deliberately Out of Scope

- **Scraping Google Maps directly.** It violates their terms of use, breaks on every layout change
  and does not belong in a public portfolio project. The whole point of the provider abstraction is
  that licensed sources are a first class path.
- **Head counts.** No provider offers them, and the percentage of peak cannot be converted into one.
  Presenting a person count would be inventing data.
- **Predicting the future beyond the weekly pattern.** Weather, events and holidays move real
  footfall, and none of the sources expose the inputs needed to model that honestly.
- **A hosted version.** That would mean holding other people's API keys, which is a different
  project with different obligations.

## Dual-Licensing Readiness

Not planned. CrowdGauge stays MIT. The problem it solves is a consumer question rather than an
enterprise one, and the commercially interesting part of this space is the underlying data, which
belongs to the providers, not to this client.
