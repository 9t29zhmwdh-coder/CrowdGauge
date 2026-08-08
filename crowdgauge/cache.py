"""Small in-memory TTL cache.

Providers charge per request, so a repeated lookup of the same venue within a
few minutes should not cost another credit. Live values deliberately bypass
this cache, see providers.base.
"""

import time
from typing import Any


class TTLCache:
    """Dictionary with per entry expiry. Not thread safe by design.

    The FastAPI app runs single process, and every access happens inside the
    event loop, so a lock would only add cost here.
    """

    def __init__(self, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds
        self._entries: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        if self._ttl <= 0:
            return None
        entry = self._entries.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < time.monotonic():
            del self._entries[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        if self._ttl <= 0:
            return
        self._entries[key] = (time.monotonic() + self._ttl, value)

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)
