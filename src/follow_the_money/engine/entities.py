"""Registry-driven entity resolution (no LLM).

Design section 5: configured institutions, companies, tickers, asset
aliases resolve to canonical entity identities via an explicit registry.
Ambiguous aliases, conflicts, and unknown labels are preserved, never
invented.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from ..config.model import AppConfig, Entity


class ResolutionError(ValueError):
    """Ambiguous or conflicting entity resolution."""


@dataclass(frozen=True)
class Resolution:
    entity_id: str | None
    display_name: str
    raw: str
    ambiguous: bool = False
    conflict: bool = False


def _norm(text: str) -> str:
    nfc = unicodedata.normalize("NFC", text).casefold()
    return "".join(ch for ch in nfc if not unicodedata.category(ch).startswith(("P", "Z", "C")))


class EntityResolver:
    def __init__(self, entities: Iterable[Entity]) -> None:
        self._entities = {e.id: e for e in entities}
        self._alias_index: dict[str, list[Entity]] = {}
        for e in entities:
            names = {e.name, e.name_zh, e.id, *_aliases(e)}
            for name in names:
                key = _norm(name)
                self._alias_index.setdefault(key, []).append(e)

    def resolve(self, raw: str) -> Resolution:
        key = _norm(raw)
        if not key:
            return Resolution(None, raw, raw)
        matches = self._alias_index.get(key, [])
        unique = {e.id for e in matches}
        if len(unique) > 1:
            return Resolution(None, raw, raw, ambiguous=True, conflict=True)
        if len(unique) == 1:
            entity = matches[0]
            return Resolution(entity.id, entity.name_zh or entity.name, raw)
        # Substring/longest-match fallback for configured entities.
        best: Entity | None = None
        for e in self._entities.values():
            for alias in {e.name, e.name_zh, e.id, *_aliases(e)}:
                if (
                    key
                    and key in _norm(alias)
                    and len(_norm(alias)) > len(key) - 3
                    and (best is None or len(_norm(alias)) > len(_norm(best.name)))
                ):
                    best = e
        if best is not None:
            return Resolution(best.id, best.name_zh or best.name, raw)
        return Resolution(None, raw, raw)


def _aliases(entity: Entity) -> list[str]:
    return list(entity.aliases)


def resolve_all(config: AppConfig) -> EntityResolver:
    return EntityResolver(config.entities)


def resolve_institutions(text: str, resolver: EntityResolver) -> list[Resolution]:
    """Resolve every configured institution alias appearing in ``text``."""
    found: list[Resolution] = []
    seen_keys: set[str] = set()
    for entity in resolver._entities.values():
        for alias in {entity.name, entity.name_zh, *_aliases(entity)}:
            if alias and alias in text:
                key = f"{alias}|{text}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    found.append(resolver.resolve(alias))
    return found
