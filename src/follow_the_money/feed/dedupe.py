"""Feed normalization and conservative deduplication.

Design section 5:

- One stable item total order, ``(source.knowledge_available_at, id)``,
  governs grouping, comparison, survivor selection, dropped-ID production,
  ``source_lineage`` merging, and final serialization, so input
  permutations cannot change the semantic Feed.
- Exact normalized-URL duplicates across sources retain one deterministic
  survivor plus every source-lineage record; they are not independent
  corroboration when they share an original publisher/wire story.
- Same-source near duplicates collapse; independently originated cross-source
  reports remain separate evidence.
- Stable deterministic item IDs hash provider identity plus normalized source
  record identity.
- Duplicate timestamps with different values in one instrument are a provider
  conflict; exact duplicates collapse; serialized observations are strictly
  chronological.
"""

from __future__ import annotations

import hashlib
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

PUNCTUATION_AND_SEPARATORS = {
    cat
    for cat in (
        "Pc",
        "Pd",
        "Pe",
        "Pf",
        "Pi",
        "Po",
        "Ps",
        "Zs",
        "Zl",
        "Zp",
        "Cc",
        "Cf",
    )
}


def normalize_title(title: str) -> str:
    """Closed v1 title normalization for similarity.

    NFC normalize, Unicode-casefold, remove every Unicode
    punctuation/separator/control code point.
    """
    nfc = unicodedata.normalize("NFC", title)
    folded = nfc.casefold()
    return "".join(
        ch for ch in folded if unicodedata.category(ch) not in PUNCTUATION_AND_SEPARATORS
    )


def title_trigrams(normalized: str) -> set[str]:
    if len(normalized) < 3:
        return set()
    return {normalized[i : i + 3] for i in range(len(normalized) - 2)}


def title_jaccard(a: str, b: str) -> float:
    """Jaccard over overlapping Unicode-code-point trigrams.

    When either normalized title is shorter than three code points, only
    exact normalized equality scores 1 and every other pair scores 0.
    """
    na, nb = normalize_title(a), normalize_title(b)
    if len(na) < 3 or len(nb) < 3:
        return 1.0 if na == nb else 0.0
    ta, tb = title_trigrams(na), title_trigrams(nb)
    if not ta and not tb:
        return 1.0 if na == nb else 0.0
    return len(ta & tb) / len(ta | tb)


def stable_item_id(provider_id: str, record_identity: str) -> str:
    digest = hashlib.sha256(f"{provider_id}|{record_identity}".encode()).hexdigest()
    return f"item_{digest[:32]}"


def item_total_order_key(item: Mapping[str, Any]) -> tuple[str, str]:
    """The one stable Feed-item total order: ``(knowledge_available_at, id)``.

    Every order-sensitive Feed step (URL grouping, same-source near-dedup
    comparison, survivor selection, dropped-ID production, ``source_lineage``
    merging, and final serialization) uses this key so input permutations
    cannot change the semantic result.
    """
    source = item.get("source", {})
    return (source.get("knowledge_available_at", ""), item["id"])


def deduplicate_items(
    items: Sequence[Mapping[str, Any]],
    *,
    title_similarity_threshold: float = 0.85,
) -> tuple[list[Mapping[str, Any]], list[str]]:
    """Conservative Feed deduplication.

    - Same canonical URL: exactly one survivor keeps all lineage records.
    - Same source, near-duplicate titles (Jaccard >= threshold): collapse,
      keeping the earliest knowledge item as survivor.
    - Independent cross-source reports are retained as separate evidence.
    Returns (items, dropped_ids).

    The input is normalized to the stable ``(knowledge_available_at, id)``
    total order before grouping, comparison, survivor selection, dropped-ID
    production, and lineage merging, so input permutations cannot change the
    result.
    """
    dropped: list[str] = []
    by_url: dict[str, list[Mapping[str, Any]]] = {}
    by_source: dict[str, list[Mapping[str, Any]]] = {}

    ordered = sorted(items, key=item_total_order_key)
    for item in ordered:
        url = item.get("source", {}).get("url", "")
        by_url.setdefault(url, []).append(item)
        provider = item.get("provider_id", "")
        by_source.setdefault(provider, []).append(item)

    # 1. URL-level: collapse exact canonical-URL duplicates.
    url_survivors: list[Mapping[str, Any]] = []
    for url, group in by_url.items():
        if len(group) == 1:
            url_survivors.append(group[0])
            continue
        survivor = _merge_lineage(group)
        url_survivors.append(survivor)
        dropped.extend(i["id"] for i in group if i["id"] != survivor["id"])

    # 2. Same-source near dedup: collapse near-duplicate titles within one
    #    provider; independent cross-source reports survive.
    survivors_by_source: dict[str, list[Mapping[str, Any]]] = {}
    for item in url_survivors:
        survivors_by_source.setdefault(item.get("provider_id", ""), []).append(item)

    final: list[Mapping[str, Any]] = []
    for provider, group in sorted(survivors_by_source.items()):
        ordered = sorted(group, key=item_total_order_key)
        kept: list[Mapping[str, Any]] = []
        for item in ordered:
            title = item.get("payload", {}).get("title", "")
            duplicate = False
            for existing in kept:
                existing_title = existing.get("payload", {}).get("title", "")
                if title and title_jaccard(title, existing_title) >= title_similarity_threshold:
                    duplicate = True
                    break
            if duplicate:
                dropped.append(item["id"])
            else:
                kept.append(item)
        final.extend(kept)

    return final, list(dict.fromkeys(dropped))


def _merge_lineage(group: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    """Merge a URL-duplicate group into one survivor with full lineage.

    The contributing-item order is the stable total order
    ``(knowledge_available_at, id)``; the earliest item survives.
    """
    ordered = sorted(group, key=item_total_order_key)
    survivor = dict(ordered[0])
    lineage = []
    for item in ordered:
        src = dict(item["source"])
        lineage.append(
            {
                "id": item["id"],
                "provider_id": item["provider_id"],
                "source_id": src.get("id"),
                "original_publisher": src.get("original_publisher"),
                "syndication_origin": src.get("syndication_origin"),
            }
        )
    survivor = dict(survivor)
    survivor["source_lineage"] = lineage
    return survivor


def deduplicate_observations(
    observations: Sequence[Mapping[str, Any]],
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    """Strict-chronological observation dedup.

    Exact duplicates collapse deterministically; same timestamp with
    incompatible values is a conflict (returned separately); the serialized
    result is strictly chronological.
    """
    by_ts: dict[str, list[Mapping[str, Any]]] = {}
    for obs in observations:
        by_ts.setdefault(obs["as_of"], []).append(obs)

    cleaned: list[Mapping[str, Any]] = []
    conflicts: list[Mapping[str, Any]] = []
    for ts in sorted(by_ts):
        group = by_ts[ts]
        values = {obs["value"] for obs in group}
        if len(values) > 1:
            conflicts.append({"as_of": ts, "values": sorted(values)})
            # Do not silently select; keep the first for reference.
            cleaned.append(dict(group[0]))
        else:
            cleaned.append(dict(group[0]))
    return cleaned, conflicts


def deterministic_item_order(items: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Deterministic ordering independent of input permutation: by knowledge
    time, then stable ID (the shared Feed item total order)."""
    return sorted(items, key=item_total_order_key)
