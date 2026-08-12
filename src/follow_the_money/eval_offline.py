"""Golden-day dataset and offline evaluation runner (task 11.3-11.6).

- At least 30 unique, provenance-reviewed trading-day fixtures covering the
  required scenario categories: ordinary sessions, CPI/PCE/payroll/FOMC,
  systemically important company events, major China policy, China-US policy
  shocks, geopolitics, abnormal cross-asset moves, and provider degradation.
- Each fixture has: a Feed input, recorded four-pass outputs, expected major
  events, expected full-event labels, canonical story-family member Event
  IDs plus exact unordered ``distinct_material_development`` pairs, and
  factual/causal claim labels.
- The offline runner consumes fixed provider/market inputs with producer
  provenance, replays deterministically from the saved Feed/effective config,
  applies exact correctness gates, and fails on invalid fixtures before
  scoring.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from html import unescape
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .eval_metrics import (
    AggregateReport,
    DayReport,
    aggregate,
    causal_overclaim_rate,
    check_offline_gates,
    compare_ranking_stability,
    duplicate_story_rate,
    recall_at_10,
    top3_precision,
    unsupported_claim_rate,
)
from .feed.validate import assert_feed_identity, validate_feed
from .schema import SchemaError, validate_against

REQUIRED_CATEGORIES = (
    "ordinary_session",
    "macro_release",
    "company_event",
    "china_policy",
    "china_us_policy",
    "geopolitics",
    "abnormal_cross_asset",
    "degraded_provider",
)

MIN_DAYS = 30


class GoldenDatasetError(ValueError):
    """Golden-day fixture validation failed."""


@dataclass(frozen=True)
class GoldenDay:
    date: str
    category: str
    feed_path: str
    recorded_outputs: Mapping[str, Any]
    expected_major_events: tuple[str, ...]
    expected_top3: tuple[str, ...]
    story_family_members: Mapping[str, tuple[str, ...]]
    coexistence_pairs: tuple[tuple[str, str], ...]
    claim_labels: Mapping[str, Mapping[str, bool]]  # claim_id -> {factual, causal}
    provenance: Mapping[str, Any]

    def validate(self) -> None:
        if not self.date:
            raise GoldenDatasetError("golden day missing date")
        if self.category not in REQUIRED_CATEGORIES:
            raise GoldenDatasetError(f"{self.date}: unknown category {self.category!r}")
        if not self.expected_major_events:
            raise GoldenDatasetError(f"{self.date}: no expected major events")
        if len(self.expected_top3) > 3:
            raise GoldenDatasetError(f"{self.date}: expected Top-3 exceeds 3")
        for fam, members in self.story_family_members.items():
            if len(members) < 2:
                raise GoldenDatasetError(f"{self.date}: family {fam} must have >=2 members")
        for a, b in self.coexistence_pairs:
            if a == b:
                raise GoldenDatasetError(f"{self.date}: self coexistence pair {a}")


def _fixture_path(dataset_dir: Path, value: str, *, field: str, date: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise GoldenDatasetError(f"{date}: unsafe {field} fixture path {value!r}")
    resolved = dataset_dir / path
    if not resolved.is_file():
        raise GoldenDatasetError(f"{date}: fixture missing for {field}: {resolved}")
    return resolved


def _load_fixture_json(path: Path, *, date: str, field: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        raise GoldenDatasetError(f"{date}: invalid {field} fixture {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GoldenDatasetError(f"{date}: {field} fixture must be a JSON object: {path}")
    return value


def _source_excerpt(body: bytes, *, charset: str = "utf-8") -> str:
    text = body.decode(charset, errors="strict")
    text = re.sub(
        r"<(?:style|script|noscript)\b[^>]*>.*?</(?:style|script|noscript)>",
        " ",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", unescape(text)).strip()[:240]


def _bounded_source_fragment(text: str) -> str:
    normalized = " ".join(text.split())
    return normalized[:132] or "来源记录未提供可显示文本。"


def _source_title(body: bytes, *, charset: str = "utf-8") -> str:
    text = body.decode(charset, errors="strict")
    if text.lstrip().startswith("{"):
        payload = json.loads(text)
        symbol = payload["chart"]["result"][0]["meta"]["symbol"]
        return f"Yahoo Finance historical chart for {symbol}"
    if "<dataroot" in text.lower():
        type_ids = sorted(set(re.findall(r"<typeid>([^<]+)</typeid>", text)))
        return f"PBOC exchange-rate XML typeid={','.join(type_ids)}"
    for pattern in (
        r'<meta\b[^>]*\bproperty=["\']og:title["\'][^>]*\bcontent=["\'](.*?)["\']',
        r'<meta\b[^>]*\bcontent=["\'](.*?)["\'][^>]*\bproperty=["\']og:title["\']',
        r"<h1\b[^>]*>(.*?)</h1>",
        r"<title\b[^>]*>(.*?)</title>",
    ):
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            value = re.sub(r"<[^>]+>", " ", unescape(match.group(1)))
            value = re.sub(r"\s+", " ", value).strip()
            if value:
                return value[:300]
    return _source_excerpt(body, charset=charset)[:300]


def _pboc_observation(body: bytes, date: str, *, charset: str = "utf-8") -> dict[str, str] | None:
    text = body.decode(charset, errors="strict")
    match = re.search(
        rf"<Temp>\s*<date>{re.escape(date)}</date>\s*<hlvalue>([^<]+)</hlvalue>\s*<typeid>([^<]+)</typeid>",
        text,
        re.DOTALL,
    )
    if match is None:
        return None
    return {"date": date, "value": match.group(1), "type_id": match.group(2)}


def _source_date_present(
    date: str, body: bytes, source_url: str, *, charset: str = "utf-8"
) -> bool:
    text = body.decode(charset, errors="strict")
    year, month, day = date.split("-")
    return any(
        token in text or token in source_url
        for token in (
            date,
            f"{year}年{int(month)}月{int(day)}日",
            f"{year}年{month}月{day}日",
            f"{year}{month}{day}",
            f"{month}{day}{year}",
        )
    )


def _source_timestamp(provider: str, date: str, body: bytes, *, charset: str = "utf-8") -> str:
    text = body.decode(charset, errors="strict")
    if provider == "sec_edgar":
        accepted = re.search(
            r"Accepted</div>\s*<div class=\"info\">"
            r"(\d{4}-\d{2}-\d{2})(?:\s+(\d{2}:\d{2}:\d{2}))?",
            text,
            re.DOTALL,
        )
        if accepted:
            return f"{accepted.group(1)}T{accepted.group(2) or '00:00:00'}Z"
    year, month, day = date.split("-")
    english_date = rf"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+0?{int(day)},\s+{year}"
    date_patterns = (
        (english_date,)
        if provider == "bls"
        else (
            rf"{year}-{month}-{day}",
            rf"{year}年0?{int(month)}月0?{int(day)}日",
            rf"{year}{month}{day}",
            rf"{month}{day}{year}",
            english_date,
        )
    )
    match = next(
        (found for pattern in date_patterns if (found := re.search(pattern, text, re.IGNORECASE))),
        None,
    )
    if match is None:
        raise GoldenDatasetError(f"{date}: source body has no matching event date")
    context = text[max(0, match.start() - 120) : match.end() + 120]
    time_match = re.search(
        r"(?<!\d)(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(a\.m\.|p\.m\.)?",
        context,
        re.IGNORECASE,
    )
    hour = int(time_match.group(1)) if time_match else 0
    minute = int(time_match.group(2)) if time_match else 0
    second = int(time_match.group(3) or 0) if time_match else 0
    if time_match and time_match.group(4):
        meridiem = time_match.group(4).lower()
        if meridiem.startswith("p") and hour < 12:
            hour += 12
        if meridiem.startswith("a") and hour == 12:
            hour = 0
    parsed_date = datetime.fromisoformat(f"{date}T00:00:00")
    parsed_date = parsed_date.replace(
        tzinfo=ZoneInfo("America/New_York") if provider == "bls" else UTC,
        hour=hour,
        minute=minute,
        second=second,
    )
    return parsed_date.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_source_payload_semantics(
    *, date: str, item: Mapping[str, Any], body: bytes, metadata: Mapping[str, Any]
) -> None:
    payload = item.get("payload")
    raw_metadata = payload.get("raw_metadata") if isinstance(payload, dict) else None
    if not isinstance(payload, dict) or not isinstance(raw_metadata, dict):
        raise GoldenDatasetError(f"{date}: Feed payload lacks source metadata")
    if metadata.get("provider_id") != item.get("provider_id"):
        raise GoldenDatasetError(f"{date}: source provider does not match Feed provider")
    if metadata.get("date") != date:
        raise GoldenDatasetError(f"{date}: source metadata date is not fixture-bound")
    charset = str(metadata.get("body_charset", "utf-8"))
    if charset not in {"utf-8", "windows-1252"}:
        raise GoldenDatasetError(f"{date}: source charset is not allowlisted")
    try:
        body.decode(charset, errors="strict")
    except UnicodeDecodeError as exc:
        raise GoldenDatasetError(f"{date}: source body is not valid {charset}") from exc
    source_title = _source_title(body, charset=charset)
    if metadata.get("title") != source_title:
        raise GoldenDatasetError(f"{date}: source metadata title is not body-derived")
    if raw_metadata.get("source_title") != source_title:
        raise GoldenDatasetError(f"{date}: Feed source title is not body-derived")
    if raw_metadata.get("source_excerpt") != _source_excerpt(body, charset=charset):
        raise GoldenDatasetError(f"{date}: Feed source excerpt is not body-derived")

    provider_id = item.get("provider_id")
    source_url = str(item.get("source", {}).get("url", ""))
    if provider_id != "yahoo_market" and not _source_date_present(
        date, body, source_url, charset=charset
    ):
        raise GoldenDatasetError(f"{date}: source date is not body/URL-derived")
    payload_type = str(payload.get("type", ""))
    if payload_type in {"news", "policy"} and payload.get("title") != source_title:
        raise GoldenDatasetError(f"{date}: payload title is not source-derived")
    if payload_type == "macro_release" and raw_metadata.get("source_title") != source_title:
        raise GoldenDatasetError(f"{date}: macro source title is not source-derived")
    timestamp_field = {
        "news": "occurred_at",
        "policy": "announced_at",
        "macro_release": "released_at",
        "filing": "filed_at",
    }.get(payload_type)
    if timestamp_field and not str(payload.get(timestamp_field, "")).startswith(date):
        raise GoldenDatasetError(f"{date}: payload timestamp is not source-date bound")
    if timestamp_field:
        try:
            expected_timestamp = _source_timestamp(str(provider_id), date, body, charset=charset)
        except (ValueError, TypeError) as exc:
            raise GoldenDatasetError(f"{date}: source timestamp cannot be derived") from exc
        if payload.get(timestamp_field) != expected_timestamp:
            raise GoldenDatasetError(f"{date}: payload timestamp is not body-derived")

    if provider_id == "pboc":
        expected_observation = _pboc_observation(body, date, charset=charset)
        recorded_observation = raw_metadata.get("source_observation")
        if expected_observation is not None and recorded_observation != expected_observation:
            raise GoldenDatasetError(f"{date}: PBOC observation is not source-derived")
    if provider_id == "yahoo_market":
        try:
            result = json.loads(body)["chart"]["result"][0]
            symbol = result["meta"]["symbol"]
            timestamps = result["timestamp"]
            closes = result["indicators"]["quote"][0]["close"]
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise GoldenDatasetError(f"{date}: invalid Yahoo source payload") from exc
        if payload.get("instrument_id") != symbol:
            raise GoldenDatasetError(f"{date}: Yahoo instrument is not source-derived")
        observations = payload.get("observations")
        if not isinstance(observations, list) or len(observations) != 1:
            raise GoldenDatasetError(f"{date}: Yahoo observation projection is invalid")
        observation = observations[0]
        source_values = {
            datetime.fromtimestamp(int(timestamp), UTC).strftime("%Y-%m-%dT%H:%M:%SZ"): format(
                Decimal(str(close)).normalize(), "f"
            )
            for timestamp, close in zip(timestamps, closes, strict=True)
            if close is not None
        }
        if source_values.get(observation.get("as_of")) != observation.get("value"):
            raise GoldenDatasetError(f"{date}: Yahoo observation is not source-derived")

    if provider_id == "sec_edgar":
        text = body.decode("utf-8", errors="replace")
        form_match = re.search(r"\bForm\s+([A-Z0-9]+(?:-[A-Z0-9]+)?)\b", text, re.IGNORECASE)
        filed_date = re.search(
            r"(?:Filing Date|FILED AS OF DATE).*?(\d{4}-\d{2}-\d{2})",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        accession = str(payload.get("accession_number", ""))
        if form_match is None or payload.get("form", "").upper() != form_match.group(1).upper():
            raise GoldenDatasetError(f"{date}: SEC form is not source-derived")
        accession_in_source = accession in source_url.replace("-", "")
        if accession not in text.replace("-", "") and not accession_in_source:
            raise GoldenDatasetError(f"{date}: SEC accession is not source-derived")
        if filed_date is not None and not str(payload.get("filed_at", "")).startswith(
            filed_date.group(1)
        ):
            raise GoldenDatasetError(f"{date}: SEC filing date is not source-derived")


def _validate_recorded_outputs(
    *,
    date: str,
    dataset_dir: Path,
    feed: Mapping[str, Any],
    outputs: Mapping[str, Any],
    expected_major: Sequence[str],
    expected_top3: Sequence[str],
    claim_labels: Mapping[str, Mapping[str, bool]],
    story_families: Mapping[str, Sequence[str]],
    coexistence_pairs: Sequence[Sequence[str]],
) -> None:
    if outputs.get("schema_version") != 1:
        raise GoldenDatasetError(f"{date}: recorded outputs schema_version must be 1")
    if outputs.get("feed_run_id") != feed.get("run_id"):
        raise GoldenDatasetError(f"{date}: recorded outputs feed_run_id does not match Feed run_id")
    selected = outputs.get("selected_event_ids")
    full = outputs.get("full_event_ids")
    if not isinstance(selected, list) or not all(isinstance(value, str) for value in selected):
        raise GoldenDatasetError(f"{date}: recorded selected_event_ids must be a string array")
    if not isinstance(full, list) or not all(isinstance(value, str) for value in full):
        raise GoldenDatasetError(f"{date}: recorded full_event_ids must be a string array")
    if len(full) > 3 or not set(full).issubset(selected):
        raise GoldenDatasetError(
            f"{date}: recorded full_event_ids is not a valid up-to-three subset"
        )
    if not set(expected_major).issubset(selected):
        raise GoldenDatasetError(f"{date}: recorded selection omits an expected major event")
    if not set(expected_top3).issubset(full):
        raise GoldenDatasetError(f"{date}: recorded full selection omits an expected Top-3 event")
    if selected and not feed.get("items"):
        raise GoldenDatasetError(f"{date}: selected Events are not present in the saved Feed")

    feed_item_ids = {item.get("id") for item in feed.get("items", []) if isinstance(item, dict)}
    source_fragment_by_event: dict[str, str] = {}
    for item in feed.get("items", []):
        if not isinstance(item, dict):
            raise GoldenDatasetError(f"{date}: Feed item must be an object")
        source = item.get("source")
        payload = item.get("payload")
        raw_metadata = payload.get("raw_metadata") if isinstance(payload, dict) else None
        snapshot_ref = (
            raw_metadata.get("source_snapshot") if isinstance(raw_metadata, dict) else None
        )
        if not isinstance(source, dict) or not isinstance(snapshot_ref, dict):
            raise GoldenDatasetError(f"{date}: Feed item lacks independent source snapshot")
        metadata_file = snapshot_ref.get("metadata_file")
        if not isinstance(metadata_file, str):
            raise GoldenDatasetError(f"{date}: source snapshot metadata file is invalid")
        metadata_path = _fixture_path(
            dataset_dir, f"sources/{metadata_file}", field="source snapshot metadata", date=date
        )
        metadata = _load_fixture_json(metadata_path, date=date, field="source snapshot metadata")
        body_file = metadata.get("body_file")
        if not isinstance(body_file, str):
            raise GoldenDatasetError(f"{date}: source snapshot body file is invalid")
        body_path = _fixture_path(
            dataset_dir, f"sources/{body_file}", field="source snapshot body", date=date
        )
        body = body_path.read_bytes()
        body_sha256 = hashlib.sha256(body).hexdigest()
        if (
            metadata.get("source_url") != source.get("url")
            or metadata.get("http_status") != 200
            or metadata.get("body_size") != len(body)
            or metadata.get("body_sha256") != body_sha256
            or snapshot_ref.get("body_sha256") != body_sha256
            or snapshot_ref.get("body_size") != len(body)
            or snapshot_ref.get("body_charset") != metadata.get("body_charset", "utf-8")
        ):
            raise GoldenDatasetError(f"{date}: source snapshot does not match Feed evidence")
        _validate_source_payload_semantics(date=date, item=item, body=body, metadata=metadata)
        if isinstance(raw_metadata, dict) and isinstance(raw_metadata.get("event_id"), str):
            event_id = raw_metadata["event_id"]
            source_fragment_by_event[event_id] = _bounded_source_fragment(
                str(raw_metadata["source_excerpt"])
            )
    event_evidence = outputs.get("event_evidence")
    if not isinstance(event_evidence, dict):
        raise GoldenDatasetError(f"{date}: event_evidence cross-reference is missing")
    if set(event_evidence) != set(selected):
        raise GoldenDatasetError(f"{date}: event_evidence does not cover selected Events")
    for event_id in selected:
        refs = event_evidence.get(event_id)
        if (
            not isinstance(refs, list)
            or not refs
            or not all(isinstance(ref, str) and ref in feed_item_ids for ref in refs)
        ):
            raise GoldenDatasetError(f"{date}: Event {event_id} has invalid Feed evidence refs")

    passes = outputs.get("recorded_llm_outputs")
    if not isinstance(passes, dict) or set(passes) != {
        "resolver",
        "analyst",
        "editor",
        "language-audit",
    }:
        raise GoldenDatasetError(f"{date}: recorded four-pass outputs are incomplete")
    for pass_name in ("resolver", "analyst", "editor", "language-audit"):
        if not passes[pass_name]:
            raise GoldenDatasetError(f"{date}: recorded {pass_name} output is empty")
    pass_schema_names = {
        "resolver": "resolver-output.schema.json",
        "analyst": "analyst-output.schema.json",
        "editor": "editor-output.schema.json",
        "language-audit": "language-audit-output.schema.json",
    }
    for pass_name, schema_name in pass_schema_names.items():
        try:
            validate_against(schema_name, passes[pass_name])
        except SchemaError as exc:
            raise GoldenDatasetError(f"{date}: recorded {pass_name} schema invalid: {exc}") from exc

    # Recorded pass prose must carry a bounded source-derived fragment in
    # addition to its reference aliases. This prevents an all-template pass
    # set from passing merely because its IDs and schemas are well-formed.
    replay_contract = outputs.get("replay_contract")
    if not isinstance(replay_contract, dict):
        raise GoldenDatasetError(f"{date}: replay_contract is missing")
    analyst_packets = replay_contract.get("analyst_packets")
    if not isinstance(analyst_packets, list) or len(analyst_packets) != len(selected):
        raise GoldenDatasetError(f"{date}: analyst packet replay set is incomplete")
    analyst_mapping = replay_contract.get("analyst")
    editor_mapping = replay_contract.get("editor")
    if not isinstance(analyst_mapping, dict) or not isinstance(editor_mapping, dict):
        raise GoldenDatasetError(f"{date}: pass replay mappings are incomplete")
    analyst_aliases = analyst_mapping.get("event_aliases", {})
    for event_id in selected:
        packet_alias = analyst_aliases.get(event_id)
        packet = next(
            (
                item
                for item in analyst_packets
                if isinstance(item, dict) and item.get("packet_alias") == packet_alias
            ),
            None,
        )
        fragment = source_fragment_by_event.get(event_id)
        if not isinstance(packet, dict) or not fragment:
            raise GoldenDatasetError(f"{date}: analyst source binding is incomplete for {event_id}")
        prose = [
            *packet.get("mechanisms", []),
            *packet.get("implications", []),
            packet.get("price_in", {}).get("explanation", ""),
            *packet.get("alternatives", []),
            *packet.get("watch_points", []),
        ]
        if not any(fragment in str(value) for value in prose):
            raise GoldenDatasetError(f"{date}: analyst output is not source-bound for {event_id}")

    editor_aliases = editor_mapping.get("event_aliases", {})
    slots = {slot.get("slot_alias"): slot for slot in passes["editor"].get("filled_slots", [])}
    for event_id in selected:
        slot = slots.get(editor_aliases.get(event_id))
        fragment = source_fragment_by_event.get(event_id)
        if (
            not isinstance(slot, dict)
            or not fragment
            or fragment not in str(slot.get("wording_fragment", ""))
        ):
            raise GoldenDatasetError(f"{date}: editor output is not source-bound for {event_id}")

    pass_files = outputs.get("recorded_output_files")
    if not isinstance(pass_files, dict) or set(pass_files) != set(pass_schema_names):
        raise GoldenDatasetError(f"{date}: recorded pass file references are incomplete")
    for pass_name in pass_schema_names:
        pass_path_value = pass_files[pass_name]
        if not isinstance(pass_path_value, str):
            raise GoldenDatasetError(f"{date}: recorded {pass_name} file reference is invalid")
        pass_path = _fixture_path(
            dataset_dir, pass_path_value, field=f"recorded {pass_name}", date=date
        )
        saved_pass = _load_fixture_json(pass_path, date=date, field=f"recorded {pass_name}")
        if saved_pass != passes[pass_name]:
            raise GoldenDatasetError(f"{date}: inline and referenced {pass_name} outputs differ")

    # Event membership is derived from the Feed item's curator-owned metadata,
    # then each strict pass is checked against the separate replay contract.
    feed_event_by_item: dict[str, str] = {}
    for item in feed.get("items", []):
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        event_id = (item.get("payload") or {}).get("raw_metadata", {}).get("event_id")
        if isinstance(item_id, str) and isinstance(event_id, str):
            feed_event_by_item[item_id] = event_id
    if set(feed_event_by_item.values()) != set(selected):
        raise GoldenDatasetError(f"{date}: Feed evidence does not cover selected Events")
    for event_id, refs in event_evidence.items():
        if any(feed_event_by_item.get(ref) != event_id for ref in refs):
            raise GoldenDatasetError(f"{date}: Event {event_id} evidence membership is invalid")

    replay_contract = outputs.get("replay_contract")
    if not isinstance(replay_contract, dict):
        raise GoldenDatasetError(f"{date}: replay_contract is missing")
    resolver_contract = replay_contract.get("resolver")
    analyst_contract = replay_contract.get("analyst")
    editor_contract = replay_contract.get("editor")
    if not isinstance(resolver_contract, dict):
        raise GoldenDatasetError(f"{date}: resolver replay mapping is incomplete")
    if not isinstance(analyst_contract, dict):
        raise GoldenDatasetError(f"{date}: analyst replay mapping is incomplete")
    if not isinstance(editor_contract, dict):
        raise GoldenDatasetError(f"{date}: editor replay mapping is incomplete")
    evidence_aliases = replay_contract.get("evidence_aliases")
    if not isinstance(evidence_aliases, dict):
        raise GoldenDatasetError(f"{date}: evidence replay mapping is incomplete")

    resolver_aliases = resolver_contract.get("event_aliases")
    if not isinstance(resolver_aliases, dict) or set(resolver_aliases) != set(selected):
        raise GoldenDatasetError(f"{date}: resolver Event mapping is incomplete")
    proposals = passes["resolver"].get("proposals", [])
    proposal_by_alias = {p.get("position_alias"): p for p in proposals if isinstance(p, dict)}
    if set(resolver_aliases.values()) != set(proposal_by_alias):
        raise GoldenDatasetError(f"{date}: resolver proposal mapping is not replayable")
    for event_id, alias in resolver_aliases.items():
        proposal = proposal_by_alias.get(alias)
        if not proposal or set(proposal.get("evidence_ids", [])) != set(event_evidence[event_id]):
            raise GoldenDatasetError(f"{date}: resolver evidence does not match Event {event_id}")

    def _validate_analyst_refs(event_id: str, packet_alias: str) -> None:
        packet = next(
            (
                p
                for p in passes["analyst"].get("_packets", [])
                if p.get("packet_alias") == packet_alias
            ),
            None,
        )
        if packet is None:
            raise GoldenDatasetError(f"{date}: analyst packet mapping is not replayable")
        aliases = evidence_aliases.get(event_id, {})
        if not isinstance(aliases, dict) or not aliases:
            raise GoldenDatasetError(f"{date}: analyst evidence aliases missing for {event_id}")
        references = set()
        price_in = packet.get("price_in", {})
        references.update(price_in.get("reference_aliases", []))
        references.update(packet.get("indirect_indication", {}).get("reference_aliases", []))
        for entry in packet.get("reaction_attributions", []) + packet.get("asset_mappings", []):
            references.update(entry.get("reference_aliases", []))
        if not references or not references.issubset(aliases):
            raise GoldenDatasetError(
                f"{date}: analyst references are not Feed-backed for {event_id}"
            )
        if {aliases[ref] for ref in references} - set(event_evidence[event_id]):
            raise GoldenDatasetError(f"{date}: analyst references escape Event {event_id}")

    analyst_aliases = analyst_contract.get("event_aliases")
    if not isinstance(analyst_aliases, dict) or set(analyst_aliases) != set(selected):
        raise GoldenDatasetError(f"{date}: analyst Event mapping is incomplete")
    # The strict analyst schema is one packet per invocation. The fixture
    # stores the packets in the replay contract and validates each payload
    # against the same schema below.
    analyst_packets = replay_contract.get("analyst_packets")
    if not isinstance(analyst_packets, list) or len(analyst_packets) != len(selected):
        raise GoldenDatasetError(f"{date}: analyst packet replay set is incomplete")
    for packet in analyst_packets:
        try:
            validate_against("analyst-output.schema.json", packet)
        except SchemaError as exc:
            raise GoldenDatasetError(f"{date}: analyst packet schema invalid: {exc}") from exc
    passes["analyst"] = dict(passes["analyst"])
    passes["analyst"]["_packets"] = analyst_packets
    for event_id, packet_alias in analyst_aliases.items():
        _validate_analyst_refs(event_id, packet_alias)

    editor_aliases = editor_contract.get("event_aliases")
    if not isinstance(editor_aliases, dict) or set(editor_aliases) != set(selected):
        raise GoldenDatasetError(f"{date}: editor Event mapping is incomplete")
    slots = {slot.get("slot_alias"): slot for slot in passes["editor"].get("filled_slots", [])}
    if set(editor_aliases.values()) != set(slots):
        raise GoldenDatasetError(f"{date}: editor slot mapping is not replayable")
    for event_id, slot_alias in editor_aliases.items():
        slot = slots[slot_alias]
        aliases = evidence_aliases.get(event_id, {})
        references = set(slot.get("reference_aliases", []))
        if not references or not references.issubset(aliases):
            raise GoldenDatasetError(
                f"{date}: editor references are not Feed-backed for {event_id}"
            )
        if {aliases[ref] for ref in references} - set(event_evidence[event_id]):
            raise GoldenDatasetError(f"{date}: editor references escape Event {event_id}")
    audit_output = passes["language-audit"]
    if set(audit_output.get("covered_claim_ids", [])) != set(claim_labels):
        raise GoldenDatasetError(f"{date}: recorded language-audit claim coverage is incomplete")

    inventory = outputs.get("claim_inventory")
    if not isinstance(inventory, list):
        raise GoldenDatasetError(f"{date}: recorded claim_inventory must be an array")
    inventory_ids = {item.get("claim_id") for item in inventory if isinstance(item, dict)}
    if any(
        not isinstance(item, dict) or not isinstance(item.get("claim_id"), str)
        for item in inventory
    ):
        raise GoldenDatasetError(f"{date}: recorded claim_inventory contains an invalid claim")
    if set(claim_labels) != inventory_ids:
        raise GoldenDatasetError(f"{date}: claim labels do not cover the recorded claim inventory")
    for claim_id, label in claim_labels.items():
        item = next(item for item in inventory if item["claim_id"] == claim_id)
        if item.get("is_factual") != bool(label.get("factual")) or item.get("is_causal") != bool(
            label.get("causal")
        ):
            raise GoldenDatasetError(f"{date}: claim label mismatch for {claim_id}")
        if item.get("supported") is not True or item.get("causal_overclaim") is not False:
            raise GoldenDatasetError(f"{date}: recorded claim audit is not clean for {claim_id}")
        event_ids = item.get("event_ids", [])
        evidence_ids = item.get("evidence_ids", [])
        selected_evidence = {ref for event_id in selected for ref in event_evidence[event_id]}
        if (
            not isinstance(event_ids, list)
            or not set(event_ids).issubset(set(selected))
            or not isinstance(evidence_ids, list)
            or not evidence_ids
            or not set(evidence_ids).issubset(selected_evidence)
        ):
            raise GoldenDatasetError(f"{date}: claim {claim_id} has invalid cross-references")

    selected_set = set(selected)
    for family, members in story_families.items():
        if not set(members).issubset(selected_set):
            raise GoldenDatasetError(
                f"{date}: story family {family} references an unselected Event"
            )
    canonical_pairs: set[tuple[str, str]] = set()
    for pair in coexistence_pairs:
        if len(pair) != 2 or pair[0] == pair[1]:
            raise GoldenDatasetError(f"{date}: invalid coexistence pair {pair!r}")
        normalized = tuple(sorted(pair))
        assert len(normalized) == 2
        normalized_pair = (normalized[0], normalized[1])
        if normalized_pair in canonical_pairs:
            raise GoldenDatasetError(f"{date}: duplicate coexistence pair {pair!r}")
        canonical_pairs.add(normalized_pair)
        if not set(normalized_pair).issubset(selected_set):
            raise GoldenDatasetError(f"{date}: coexistence pair references an unselected Event")

    ranking = outputs.get("ranking")
    if not isinstance(ranking, dict):
        raise GoldenDatasetError(f"{date}: recorded ranking permutation trace is missing")
    required_ranking = {
        "reference_selected",
        "permuted_selected",
        "reference_full",
        "permuted_full",
    }
    if set(ranking) != required_ranking:
        raise GoldenDatasetError(f"{date}: recorded ranking permutation trace is incomplete")
    if (
        ranking["reference_selected"] != ranking["permuted_selected"]
        or ranking["reference_full"] != ranking["permuted_full"]
    ):
        raise GoldenDatasetError(f"{date}: recorded ranking permutation is not stable")


def load_golden_dataset(dataset_dir: Path) -> tuple[GoldenDay, ...]:
    """Load and validate the golden-day dataset from ``dataset_dir``."""
    days: list[GoldenDay] = []
    seen_dates: set[str] = set()
    manifest_path = dataset_dir / "manifest.json"
    if not manifest_path.exists():
        raise GoldenDatasetError(f"dataset manifest missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_bytes())
    if manifest.get("version") != 1:
        raise GoldenDatasetError("dataset manifest version must be 1")

    for entry in manifest.get("days", []):
        date = entry["date"]
        if entry.get("category") not in REQUIRED_CATEGORIES:
            raise GoldenDatasetError(f"{date}: unknown category {entry.get('category')!r}")
        if date in seen_dates:
            raise GoldenDatasetError(f"duplicate golden day {date}")
        seen_dates.add(date)
        feed_path = _fixture_path(dataset_dir, entry["feed"], field="Feed", date=date)
        outputs_path = _fixture_path(
            dataset_dir, entry["outputs"], field="recorded outputs", date=date
        )
        feed = _load_fixture_json(feed_path, date=date, field="Feed")
        try:
            validate_feed(feed)
            assert_feed_identity(feed)
        except (SchemaError, ValueError, KeyError) as exc:
            raise GoldenDatasetError(f"{date}: invalid Feed fixture {feed_path}: {exc}") from exc
        outputs = _load_fixture_json(outputs_path, date=date, field="recorded outputs")
        expected_major = tuple(entry.get("expected_major_events", []))
        expected_top3 = tuple(entry.get("expected_top3", []))
        story_families = {k: tuple(v) for k, v in entry.get("story_families", {}).items()}
        coexistence_pairs = tuple(tuple(p) for p in entry.get("coexistence_pairs", []))
        claim_labels = {k: dict(v) for k, v in entry.get("claim_labels", {}).items()}
        _validate_recorded_outputs(
            date=date,
            dataset_dir=dataset_dir,
            feed=feed,
            outputs=outputs,
            expected_major=expected_major,
            expected_top3=expected_top3,
            claim_labels=claim_labels,
            story_families=story_families,
            coexistence_pairs=coexistence_pairs,
        )
        day = GoldenDay(
            date=date,
            category=entry["category"],
            feed_path=entry["feed"],
            recorded_outputs=outputs,
            expected_major_events=expected_major,
            expected_top3=expected_top3,
            story_family_members=story_families,
            coexistence_pairs=coexistence_pairs,
            claim_labels=claim_labels,
            provenance=entry.get("provenance", {}),
        )
        day.validate()
        days.append(day)

    if len(days) < MIN_DAYS:
        raise GoldenDatasetError(f"dataset has {len(days)} days; minimum is {MIN_DAYS}")
    categories = {d.category for d in days}
    missing = [c for c in REQUIRED_CATEGORIES if c not in categories]
    if missing:
        raise GoldenDatasetError(f"dataset missing required categories: {missing}")
    return tuple(days)


def evaluate_day(
    day: GoldenDay,
    *,
    selected_ids: Sequence[str],
    full_event_ids: Sequence[str],
    expected_major: Sequence[str] | None = None,
    expected_top3: Sequence[str] | None = None,
    non_allowed_excess: int = 0,
    factual_denominator: int = 0,
    unsupported_numerator: int = 0,
    causal_denominator: int = 0,
    overclaim_numerator: int = 0,
    audit_coverage_complete: bool = True,
    reference_selected: Sequence[str] | None = None,
    permuted_selected: Sequence[str] | None = None,
    reference_full: Sequence[str] | None = None,
    permuted_full: Sequence[str] | None = None,
) -> DayReport:
    """Compute per-day metrics and (optionally) ranking stability."""
    if not audit_coverage_complete:
        raise GoldenDatasetError(f"{day.date}: complete unique claim-audit coverage required")
    expected_major = expected_major or day.expected_major_events
    expected_top3 = expected_top3 or day.expected_top3
    metrics = {
        "recall_at_10": recall_at_10(expected_major, selected_ids),
        "top3_precision": top3_precision(expected_top3, full_event_ids),
        "duplicate_story_rate": duplicate_story_rate(selected_ids, non_allowed_excess),
        "unsupported_claim_rate": unsupported_claim_rate(
            factual_denominator, unsupported_numerator
        ),
        "causal_overclaim_rate": causal_overclaim_rate(causal_denominator, overclaim_numerator),
    }
    stability = None
    if reference_selected is not None and permuted_selected is not None:
        stability = compare_ranking_stability(
            reference_selected,
            permuted_selected,
            reference_full or [],
            permuted_full or [],
        )
    return DayReport(date=day.date, metrics=metrics, stability=stability)


def run_offline_evaluation(
    dataset_dir: Path,
    *,
    dates: Sequence[str] | None = None,
    selected_by_day: Mapping[str, Sequence[str]] | None = None,
    full_by_day: Mapping[str, Sequence[str]] | None = None,
    extras: Mapping[str, Mapping[str, Any]] | None = None,
    baseline: Mapping[str, float] | None = None,
) -> tuple[AggregateReport, list[str]]:
    """Offline runner over the golden dataset with correctness gates."""
    days = load_golden_dataset(dataset_dir)
    if dates is not None:
        wanted = set(dates)
        days = tuple(day for day in days if day.date in wanted)
        if not days:
            raise GoldenDatasetError("no golden days selected")
    reports: list[DayReport] = []
    for day in days:
        recorded = day.recorded_outputs
        selected = (selected_by_day or {}).get(day.date, recorded["selected_event_ids"])
        full = (full_by_day or {}).get(day.date, recorded["full_event_ids"])
        extras_day = (extras or {}).get(day.date, {})
        if not extras_day:
            inventory = recorded["claim_inventory"]
            extras_day = {
                "factual_denominator": sum(1 for item in inventory if item["is_factual"]),
                "unsupported_numerator": sum(
                    1 for item in inventory if item["is_factual"] and not item["supported"]
                ),
                "causal_denominator": sum(1 for item in inventory if item["is_causal"]),
                "overclaim_numerator": sum(
                    1 for item in inventory if item["is_causal"] and item["causal_overclaim"]
                ),
                "reference_selected": recorded["ranking"]["reference_selected"],
                "permuted_selected": recorded["ranking"]["permuted_selected"],
                "reference_full": recorded["ranking"]["reference_full"],
                "permuted_full": recorded["ranking"]["permuted_full"],
            }
        reports.append(
            evaluate_day(
                day,
                selected_ids=selected,
                full_event_ids=full,
                **extras_day,
            )
        )
    agg = aggregate(reports)

    # Stability gate: every drift value must be zero.
    for report in reports:
        if report.stability is not None and (
            report.stability.identity_drift
            or report.stability.selection_order_drift
            or report.stability.full_event_subset_drift
            or report.stability.full_event_order_drift
        ):
            raise GoldenDatasetError(f"{report.date}: ranking stability drift")

    # Quality gates: zero unsupported/causal overclaim; baseline deltas.
    for report in reports:
        u = report.metrics["unsupported_claim_rate"]
        c = report.metrics["causal_overclaim_rate"]
        if u.applicable and u.numerator > 0:
            raise GoldenDatasetError(f"{report.date}: unsupported claims present")
        if c.applicable and c.numerator > 0:
            raise GoldenDatasetError(f"{report.date}: causal overclaim present")

    violations: list[str] = []
    if baseline:
        current = {name: m.value for name, m in agg.metrics.items() if m.value is not None}
        violations = check_offline_gates(baseline, current)
    return agg, violations
