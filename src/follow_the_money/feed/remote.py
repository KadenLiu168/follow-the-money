"""Commit-pinned published Feed consumer."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

import httpx

from ..canonical import canonical_bytes
from .bundle import (
    MANIFEST_FILENAME,
    BundleError,
    load_feed,
    validate_manifest_and_inventory,
)

CANONICAL_REPOSITORY = "KadenLiu168/follow-the-money"
CANONICAL_BRANCH = "main"
CANONICAL_PRODUCT_ROOT = "feeds"
GITHUB_API_BASE_URL = "https://api.github.com"
RAW_BASE_URL = "https://raw.githubusercontent.com"
DISCOVERY_URL = (
    f"{GITHUB_API_BASE_URL}/repos/{CANONICAL_REPOSITORY}/git/ref/heads/{CANONICAL_BRANCH}"
)
REMOTE_TIMEOUT_SECONDS = 20.0
DISCOVERY_MAX_BYTES = 64 * 1024
MANIFEST_MAX_BYTES = 1024 * 1024
ARTIFACT_MAX_BYTES = 10 * 1024 * 1024
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class FeedRemoteError(ValueError):
    """A published Feed could not be discovered, retrieved, or consumed."""


def _response_url(response: httpx.Response, requested_url: str, where: str) -> None:
    if str(response.url) != requested_url:
        raise FeedRemoteError(f"{where}: unexpected redirect or response URL")


def _read_response(
    client: Any, url: str, *, where: str, max_bytes: int, headers: dict[str, str] | None = None
) -> bytes:
    try:
        with client.stream(
            "GET",
            url,
            headers=headers,
            follow_redirects=False,
            timeout=REMOTE_TIMEOUT_SECONDS,
        ) as response:
            _response_url(response, url, where)
            if response.status_code < 200 or response.status_code >= 300:
                raise FeedRemoteError(f"{where}: HTTP {response.status_code}")
            content_length = response.headers.get("content-length")
            if content_length is not None:
                try:
                    declared_size = int(content_length)
                except ValueError as exc:
                    raise FeedRemoteError(f"{where}: invalid Content-Length") from exc
                if declared_size > max_bytes:
                    raise FeedRemoteError(f"{where}: response exceeds {max_bytes} bytes")
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > max_bytes:
                    raise FeedRemoteError(f"{where}: response exceeds {max_bytes} bytes")
                chunks.append(chunk)
            return b"".join(chunks)
    except FeedRemoteError:
        raise
    except (httpx.HTTPError, OSError, TimeoutError) as exc:
        raise FeedRemoteError(f"{where}: {exc.__class__.__name__}") from exc


def _resolve_commit(client: Any) -> str:
    body = _read_response(
        client,
        DISCOVERY_URL,
        where="Git reference discovery",
        max_bytes=DISCOVERY_MAX_BYTES,
        headers={"Accept": "application/vnd.github+json"},
    )
    try:
        payload = json.loads(body.decode("utf-8"))
    except (ValueError, RecursionError) as exc:
        raise FeedRemoteError(f"Git reference discovery: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise FeedRemoteError("Git reference discovery: response must be an object")
    if payload.get("ref") != f"refs/heads/{CANONICAL_BRANCH}":
        raise FeedRemoteError("Git reference discovery: unexpected ref")
    obj = payload.get("object")
    if not isinstance(obj, dict) or obj.get("type") != "commit":
        raise FeedRemoteError("Git reference discovery: object is not a commit")
    sha = obj.get("sha")
    if not isinstance(sha, str) or not _COMMIT_RE.fullmatch(sha):
        raise FeedRemoteError("Git reference discovery: invalid exact commit SHA")
    return sha


def _raw_url(commit_sha: str, relative_path: str) -> str:
    return f"{RAW_BASE_URL}/{CANONICAL_REPOSITORY}/{commit_sha}/{CANONICAL_PRODUCT_ROOT}/{relative_path}"


def consume_published_feed(*, client: Any | None = None) -> dict[str, Any]:
    """Consume one immutable published Feed snapshot without local fallback."""
    owned_client = None
    if client is None:
        owned_client = httpx.Client(timeout=REMOTE_TIMEOUT_SECONDS, follow_redirects=False)
        client = owned_client
    try:
        commit_sha = _resolve_commit(client)
        manifest_bytes = _read_response(
            client,
            _raw_url(commit_sha, MANIFEST_FILENAME),
            where="Feed manifest retrieval",
            max_bytes=MANIFEST_MAX_BYTES,
        )
        try:
            manifest, paths = validate_manifest_and_inventory(manifest_bytes)
        except BundleError as exc:
            raise FeedRemoteError(f"Feed manifest validation: {exc}") from exc

        with tempfile.TemporaryDirectory(prefix="follow-the-money-feed-") as temp_root:
            product_root = Path(temp_root)
            (product_root / MANIFEST_FILENAME).write_bytes(manifest_bytes)
            for entry, relative_path in zip(manifest["artifacts"], paths, strict=True):
                size_bytes = entry["size_bytes"]
                if size_bytes > ARTIFACT_MAX_BYTES:
                    raise FeedRemoteError(
                        f"Feed artifact {entry['domain']} exceeds {ARTIFACT_MAX_BYTES} bytes"
                    )
                data = _read_response(
                    client,
                    _raw_url(commit_sha, relative_path),
                    where=f"Feed artifact {entry['domain']} retrieval",
                    max_bytes=size_bytes,
                )
                if len(data) != size_bytes:
                    raise FeedRemoteError(
                        f"Feed artifact {entry['domain']} byte size does not match manifest"
                    )
                (product_root / relative_path).write_bytes(data)
            try:
                return load_feed(product_root)
            except (BundleError, OSError) as exc:
                raise FeedRemoteError(f"Feed bundle validation: {exc}") from exc
    except OSError as exc:
        raise FeedRemoteError(f"Feed temporary storage: {exc}") from exc
    finally:
        if owned_client is not None:
            owned_client.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="prepare-feed")
    parser.parse_args(argv)
    try:
        feed = consume_published_feed()
    except FeedRemoteError as exc:
        print(f"prepare-feed: {exc}", file=sys.stderr)
        return 1
    for warning in feed["pipeline"]["warnings"]:
        print(f"warning: {warning}", file=sys.stderr)
    sys.stdout.buffer.write(canonical_bytes(feed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
