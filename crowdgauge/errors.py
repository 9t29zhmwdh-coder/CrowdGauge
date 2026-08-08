"""Error types shared by all providers.

Provider errors carry a message that is safe to show to the user. Upstream
payloads and credentials are deliberately kept out of these messages, because
the web layer forwards them straight into an HTTP response.
"""


class CrowdGaugeError(Exception):
    """Base class for every error CrowdGauge raises on purpose."""


class ProviderNotConfigured(CrowdGaugeError):
    """Raised when a provider is selected but its credentials are missing."""


class VenueNotFound(CrowdGaugeError):
    """Raised when a search returns no usable venue for the given query."""


class BusynessUnavailable(CrowdGaugeError):
    """Raised when a venue exists but the provider has no footfall data for it.

    This is the normal case for small or rarely visited places, so it is a
    distinct error rather than an upstream failure.
    """


class UpstreamError(CrowdGaugeError):
    """Raised when the provider API fails, times out or answers unparseably."""
