"""
rate_limiter.py — Per-provider rate limiting with automatic fallback.
"""

import time
import threading
from collections import deque
from typing import Optional

from config import PROVIDERS


class ProviderRateLimiter:
    """Tracks request timestamps for a single provider and enforces limits."""

    def __init__(self, provider_id: str):
        self.provider_id = provider_id
        cfg = PROVIDERS.get(provider_id, {})
        self.rpm_limit: int = cfg.get("rate_limit_rpm", 60)
        self.rpd_limit: int = cfg.get("rate_limit_rpd", 10000)

        self._lock = threading.Lock()
        # Timestamps (epoch seconds) of recent requests
        self._minute_window: deque = deque()
        self._day_window: deque = deque()

    def _prune(self) -> None:
        now = time.time()
        minute_ago = now - 60
        day_ago = now - 86400
        while self._minute_window and self._minute_window[0] < minute_ago:
            self._minute_window.popleft()
        while self._day_window and self._day_window[0] < day_ago:
            self._day_window.popleft()

    def can_request(self) -> bool:
        """Return True if a request is allowed right now."""
        with self._lock:
            self._prune()
            return (len(self._minute_window) < self.rpm_limit and
                    len(self._day_window) < self.rpd_limit)

    def record_request(self) -> None:
        """Record that a request was made."""
        with self._lock:
            now = time.time()
            self._minute_window.append(now)
            self._day_window.append(now)

    def stats(self) -> dict:
        """Return current usage statistics."""
        with self._lock:
            self._prune()
            return {
                "provider": self.provider_id,
                "rpm_used": len(self._minute_window),
                "rpm_limit": self.rpm_limit,
                "rpd_used": len(self._day_window),
                "rpd_limit": self.rpd_limit,
                "available": (len(self._minute_window) < self.rpm_limit and
                              len(self._day_window) < self.rpd_limit),
            }


class RateLimiterRegistry:
    """Global registry of per-provider rate limiters."""

    def __init__(self):
        self._limiters: dict[str, ProviderRateLimiter] = {
            pid: ProviderRateLimiter(pid) for pid in PROVIDERS
        }

    def get(self, provider_id: str) -> ProviderRateLimiter:
        if provider_id not in self._limiters:
            self._limiters[provider_id] = ProviderRateLimiter(provider_id)
        return self._limiters[provider_id]

    def can_request(self, provider_id: str) -> bool:
        return self.get(provider_id).can_request()

    def record_request(self, provider_id: str) -> None:
        self.get(provider_id).record_request()

    def all_stats(self) -> list[dict]:
        return [limiter.stats() for limiter in self._limiters.values()]

    def find_available_fallback(self, preferred_provider: str,
                                provider_type: Optional[str] = None) -> Optional[str]:
        """
        Return the first available provider that isn't rate-limited.
        Prefers the `preferred_provider`, then tries others of the same type,
        then any available provider.
        """
        if self.can_request(preferred_provider):
            return preferred_provider

        pref_type = PROVIDERS.get(preferred_provider, {}).get("type")

        # Try same-type providers first
        for pid, cfg in PROVIDERS.items():
            if pid == preferred_provider:
                continue
            if cfg.get("type") == pref_type and self.can_request(pid):
                return pid

        # Try any provider
        for pid in PROVIDERS:
            if pid != preferred_provider and self.can_request(pid):
                return pid

        return None


# Module-level singleton
_registry: Optional[RateLimiterRegistry] = None


def get_registry() -> RateLimiterRegistry:
    global _registry
    if _registry is None:
        _registry = RateLimiterRegistry()
    return _registry
