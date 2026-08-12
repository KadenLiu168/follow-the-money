"""Fetch and record the independent source snapshots used by golden days.

This is an explicit maintenance command, not part of offline evaluation. The
offline generator only consumes the checked-in snapshot metadata and bytes;
it never contacts the network.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
from datetime import UTC, date, datetime, timedelta
from http.client import IncompleteRead, RemoteDisconnected
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen

from scripts.build_golden_dataset import EVIDENCE, _source_charset, _source_title

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "evals" / "dataset"
SOURCE_ROOT = DATASET / "sources"
MAX_BYTES = 20 * 1024 * 1024
USER_AGENT = "follow-the-money-golden-source-review/1.0 contact=maintainer@example.com"


def _rows(value: tuple[str, ...] | tuple[tuple[str, ...], ...]) -> tuple[tuple[str, ...], ...]:
    if value and isinstance(value[0], str):
        return (value,)  # type: ignore[return-value]
    return value  # type: ignore[return-value]


def _event_ids() -> dict[str, tuple[str, ...]]:
    manifest = json.loads((DATASET / "manifest.json").read_bytes())
    return {str(day["date"]): tuple(day["expected_major_events"]) for day in manifest["days"]}


def _snapshot_url(source_url: str, day: str) -> str:
    parsed = urlsplit(source_url)
    if parsed.hostname == "www.bls.gov":
        # The archive page is the reviewed primary response.  The public API
        # has a shared daily quota and can return HTTP 200 with an error body;
        # that is not a valid golden-source snapshot.
        return source_url
    if parsed.hostname != "finance.yahoo.com":
        return source_url
    symbol_match = re.search(r"/quote/([^/]+)/history", parsed.path)
    if symbol_match is None:
        raise ValueError(f"cannot derive Yahoo symbol from {source_url}")
    symbol = unquote(symbol_match.group(1))
    start = date.fromisoformat(day) - timedelta(days=4)
    end = date.fromisoformat(day) + timedelta(days=2)
    period1 = int(datetime.combine(start, datetime.min.time(), tzinfo=UTC).timestamp())
    period2 = int(datetime.combine(end, datetime.min.time(), tzinfo=UTC).timestamp())
    return (
        f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
        f"?period1={period1}&period2={period2}&interval=1d&events=history"
    )


def _fetch(url: str) -> tuple[bytes, str, int, str | None]:
    for attempt in range(3):
        request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
        try:
            with urlopen(request, timeout=45) as response:
                body = response.read(MAX_BYTES + 1)
                if len(body) > MAX_BYTES:
                    raise ValueError(f"source response exceeds {MAX_BYTES} bytes: {url}")
                return (
                    body,
                    str(response.geturl()),
                    int(response.status),
                    response.headers.get("content-type"),
                )
        except HTTPError as exc:
            if exc.code not in {408, 429, 500, 502, 503, 504} or attempt == 2:
                raise
        except (IncompleteRead, RemoteDisconnected, URLError, ConnectionError, TimeoutError) as exc:
            if "UNSAFE_LEGACY_RENEGOTIATION_DISABLED" in str(exc):
                return _fetch_with_curl(url)
            if attempt == 2:
                raise
        time.sleep(1 + attempt)
    raise AssertionError("unreachable")


def _fetch_with_curl(url: str) -> tuple[bytes, str, int, str | None]:
    with NamedTemporaryFile() as body_file:
        result = subprocess.run(
            [
                "curl",
                "-L",
                "--fail",
                "--silent",
                "--show-error",
                "--max-time",
                "45",
                "-A",
                USER_AGENT,
                "-o",
                body_file.name,
                "-w",
                "%{http_code}\t%{url_effective}\t%{content_type}",
                url,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"curl failed for {url}: {result.stderr.strip()}")
        body = Path(body_file.name).read_bytes()
        status_text, final_url, content_type = result.stdout.split("\t", 2)
        return body, final_url, int(status_text), content_type or None


def main() -> int:
    SOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    event_ids = _event_ids()
    for day, value in sorted(EVIDENCE.items()):
        rows = _rows(value)
        for event_id, row in zip(event_ids[day], rows, strict=True):
            provider, _source_name, _tier, source_url, _title = row
            fetch_url = _snapshot_url(source_url, day)
            body, final_url, status, content_type = _fetch(fetch_url)
            charset = _source_charset(source_url, body)
            stem = f"{day}__{event_id}"
            body_path = SOURCE_ROOT / f"{stem}.body"
            metadata_path = SOURCE_ROOT / f"{stem}.json"
            body_path.write_bytes(body)
            metadata = {
                "schema_version": 1,
                "date": day,
                "event_id": event_id,
                "provider_id": provider,
                "source_url": source_url,
                "fetch_url": fetch_url,
                "final_url": final_url,
                "title": _source_title(body, charset=charset),
                "body_charset": charset,
                "http_status": status,
                "content_type": content_type,
                "body_file": body_path.name,
                "body_size": len(body),
                "body_sha256": hashlib.sha256(body).hexdigest(),
                "retrieved_at": "2026-08-11T00:00:00Z",
            }
            metadata_path.write_bytes(
                json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
                + b"\n"
            )
            print(f"{day} {event_id} {status} {len(body)} {source_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
