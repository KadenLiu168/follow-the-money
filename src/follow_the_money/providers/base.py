"""Small Provider protocol and explicit registry.

Design section 2:

- Each provider implements ``fetch(window, client)`` and ``normalize(raw,
  window)``; exceptions at the orchestration boundary become structured
  source outcomes. No dynamic discovery or implicit fallback.
- Provider clients contact only configured HTTPS hosts and allowlisted
  redirects, enforce response/decompression limits, use safe XML parsing,
  never dereference source URLs, and redact credentials from errors.
- The registry maps configured provider IDs to adapter instances and enforces
  the closed coverage matrix membership.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from ..config.model import ProviderEntry


@runtime_checkable
class Provider(Protocol):
    """Minimal provider adapter contract."""

    provider_id: str

    def fetch(self, window: Mapping[str, str], client: Any) -> Any:
        """Fetch raw source bytes/objects for ``[window.start, window.end]``."""

    def normalize(self, raw: Any, window: Mapping[str, str]) -> list[dict[str, Any]]:
        """Normalize raw into Feed items (each already URL-validated)."""


@dataclass(frozen=True)
class OutcomeCounters:
    attempted: int = 0
    fetched: int = 0
    accepted: int = 0
    rejected: int = 0


class ProviderRegistry:
    """Explicit registry of provider adapters."""

    def __init__(self, providers: Mapping[str, Provider]) -> None:
        self._providers = dict(providers)

    def get(self, provider_id: str) -> Provider:
        try:
            return self._providers[provider_id]
        except KeyError as exc:
            raise KeyError(f"provider {provider_id!r} not in registry") from exc

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))

    def enabled_ids(self, config_providers: Mapping[str, ProviderEntry]) -> tuple[str, ...]:
        return tuple(
            pid for pid in self.ids() if config_providers.get(pid) and config_providers[pid].enabled
        )
