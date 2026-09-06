"""Canonical-main published Feed consumer regressions."""

from __future__ import annotations

import gzip
import importlib
import inspect
import json
from pathlib import Path

import httpx
import pytest

from follow_the_money.canonical import canonical_bytes, canonical_sha256
from follow_the_money.feed.bundle import build_bundle
from follow_the_money.feed.validate import recompute_feed_identity
from tests.test_feed_boundary import _valid_v3_blocked_feed
from tests.test_feed_bundle import _feed, _news

REPOSITORY = "KadenLiu168/follow-the-money"
REPO_ROOT = Path(__file__).resolve().parents[1]


def _remote_module():
    return importlib.import_module("follow_the_money.feed.remote")


def _client_for_payloads(
    remote,
    calls: list[str],
    manifest_bytes: bytes,
    artifact_bytes: dict[str, bytes],
    *,
    failures: dict[str, object] | None = None,
    response_headers: dict[str, dict[str, str]] | None = None,
):
    failures = failures or {}
    response_headers = response_headers or {}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        calls.append(url)
        assert "api.github.com" not in url
        prefix = f"{remote.RAW_BASE_URL}/{REPOSITORY}/main/feeds/"
        assert url.startswith(prefix)
        relative = url.removeprefix(prefix)
        failure = failures.get(relative)
        if isinstance(failure, BaseException):
            raise failure
        if isinstance(failure, int):
            return httpx.Response(failure, request=request)
        if relative == "feed-manifest.json":
            return httpx.Response(
                200,
                headers=response_headers.get(relative),
                content=manifest_bytes,
                request=request,
            )
        if relative in artifact_bytes:
            return httpx.Response(
                200,
                headers=response_headers.get(relative),
                content=artifact_bytes[relative],
                request=request,
            )
        raise AssertionError(f"unexpected Feed path: {relative}")

    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)


def _client_for_bundle(bundle, remote, calls: list[str], **kwargs):
    artifacts = {
        entry["path"]: bundle.artifact_bytes[entry["domain"]]
        for entry in bundle.manifest["artifacts"]
    }
    return _client_for_payloads(remote, calls, bundle.manifest_bytes, artifacts, **kwargs)


def _payloads(bundle, manifest=None, overrides=None):
    manifest = manifest or bundle.manifest
    artifacts = {
        entry["path"]: bundle.artifact_bytes[entry["domain"]]
        for entry in bundle.manifest["artifacts"]
    }
    artifacts.update(overrides or {})
    return canonical_bytes(manifest), artifacts


def test_consumer_retrieves_manifest_first_under_canonical_main_root():
    remote = _remote_module()
    bundle = build_bundle(_feed([_news()]))
    calls: list[str] = []

    with _client_for_bundle(bundle, remote, calls) as client:
        feed = remote.consume_published_feed(client=client)

    prefix = f"{remote.RAW_BASE_URL}/{REPOSITORY}/main/feeds/"
    assert feed == _feed([_news()])
    assert calls[0] == f"{prefix}feed-manifest.json"
    assert len(calls) == 9
    assert all(url.startswith(prefix) for url in calls)
    assert all("api.github.com" not in url for url in calls)
    assert [url.removeprefix(prefix) for url in calls] == [
        "feed-manifest.json",
        *(entry["path"] for entry in bundle.manifest["artifacts"]),
    ]


def test_consumer_accepts_gzip_artifact_when_wire_length_exceeds_decoded_size():
    remote = _remote_module()
    bundle = build_bundle(_feed([_news()]))
    target = next(
        entry for entry in bundle.manifest["artifacts"] if entry["domain"] == "macro_release"
    )
    encoded = gzip.compress(bundle.artifact_bytes[target["domain"]], compresslevel=0, mtime=0)
    calls: list[str] = []

    assert len(encoded) > target["size_bytes"]
    manifest_bytes, artifacts = _payloads(bundle)
    artifacts[target["path"]] = encoded
    with _client_for_payloads(
        remote,
        calls,
        manifest_bytes,
        artifacts,
        response_headers={
            target["path"]: {
                "Content-Encoding": "gzip",
                "Content-Length": str(len(encoded)),
            }
        },
    ) as client:
        feed = remote.consume_published_feed(client=client)

    assert feed == _feed([_news()])


def test_consumer_rejects_gzip_artifact_when_decoded_size_exceeds_manifest():
    remote = _remote_module()
    bundle = build_bundle(_feed([_news()]))
    target = bundle.manifest["artifacts"][0]
    oversized = bundle.artifact_bytes[target["domain"]] + b"x"
    encoded = gzip.compress(oversized, mtime=0)
    assert len(encoded) <= target["size_bytes"] < len(oversized)
    manifest_bytes, artifacts = _payloads(bundle, overrides={target["path"]: encoded})

    with (
        _client_for_payloads(
            remote,
            [],
            manifest_bytes,
            artifacts,
            response_headers={target["path"]: {"Content-Encoding": "gzip"}},
        ) as client,
        pytest.raises(remote.FeedRemoteError, match="response exceeds"),
    ):
        remote.consume_published_feed(client=client)


def test_consumer_accepts_valid_artifact_larger_than_legacy_10_mib_limit():
    remote = _remote_module()
    item = _news()
    item["payload"]["raw_metadata"] = {"padding": "x" * (10 * 1024 * 1024)}
    feed = _feed([item])
    feed["content_digest"], feed["run_id"] = recompute_feed_identity(feed)
    bundle = build_bundle(feed)
    calls: list[str] = []

    assert bundle.manifest["artifacts"][0]["size_bytes"] > 10 * 1024 * 1024
    assert bundle.manifest["artifacts"][0]["size_bytes"] < 50 * 1024 * 1024
    with _client_for_bundle(bundle, remote, calls) as client:
        assert remote.consume_published_feed(client=client) == feed


def test_consumer_source_constants_are_closed_and_manifest_drives_inventory():
    remote = _remote_module()

    assert remote.CANONICAL_REPOSITORY == REPOSITORY
    assert remote.CANONICAL_BRANCH == "main"
    assert remote.CANONICAL_PRODUCT_ROOT == "feeds"
    assert remote.RAW_BASE_URL == "https://raw.githubusercontent.com"
    assert remote._raw_url("feed-manifest.json") == (
        f"{remote.RAW_BASE_URL}/{REPOSITORY}/main/feeds/feed-manifest.json"
    )


@pytest.mark.parametrize("status", [301, 302, 307, 308])
def test_redirect_is_rejected_without_requesting_another_source(status):
    remote = _remote_module()
    calls: list[str] = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(status, headers={"Location": "https://example.com/"}, request=request)

    with (
        httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True) as client,
        pytest.raises(remote.FeedRemoteError, match=f"HTTP {status}"),
    ):
        remote.consume_published_feed(client=client)
    assert calls == [remote._raw_url("feed-manifest.json")]


@pytest.mark.parametrize(
    "failure_kind",
    ["noncanonical", "unsupported", "missing", "duplicate", "order", "path", "cutoff"],
)
def test_invalid_manifest_is_rejected_before_artifact_retrieval(failure_kind):
    remote = _remote_module()
    bundle = build_bundle(_feed())
    manifest = json.loads(bundle.manifest_bytes)
    if failure_kind == "unsupported":
        manifest["schema_version"] = 4
    elif failure_kind == "missing":
        manifest["artifacts"].pop()
    elif failure_kind == "duplicate":
        manifest["artifacts"][1] = manifest["artifacts"][0]
    elif failure_kind == "order":
        manifest["artifacts"].reverse()
    elif failure_kind == "path":
        manifest["artifacts"][0]["path"] = "../latest.json"
    elif failure_kind == "cutoff":
        manifest["window"]["end"] = manifest["window"]["start"]
    data = canonical_bytes(manifest)
    if failure_kind == "noncanonical":
        data += b"\n"
    calls: list[str] = []
    with (
        _client_for_payloads(remote, calls, data, {}) as client,
        pytest.raises(remote.FeedRemoteError, match="Feed manifest validation"),
    ):
        remote.consume_published_feed(client=client)
    assert calls == [remote._raw_url("feed-manifest.json")]


def test_http_manifest_failure_is_typed_and_does_not_read_local_feed():
    remote = _remote_module()
    calls: list[str] = []
    bundle = build_bundle(_feed())
    with (
        _client_for_bundle(bundle, remote, calls, failures={"feed-manifest.json": 403}) as client,
        pytest.raises(remote.FeedRemoteError, match="HTTP 403"),
    ):
        remote.consume_published_feed(client=client)

    assert calls == [remote._raw_url("feed-manifest.json")]


def test_degraded_bundle_preserves_warnings_and_provider_availability_without_recheck():
    remote = _remote_module()
    feed = _valid_v3_blocked_feed()
    feed["content_digest"], feed["run_id"] = recompute_feed_identity(feed)
    bundle = build_bundle(feed)
    calls: list[str] = []

    with _client_for_bundle(bundle, remote, calls) as client:
        consumed = remote.consume_published_feed(client=client)

    assert consumed["pipeline"] == feed["pipeline"]
    assert consumed["provider_outcomes"] == feed["provider_outcomes"]
    assert len(calls) == 9


@pytest.mark.parametrize(
    "failure_kind",
    [
        "missing",
        "short",
        "oversized",
        "sha256",
        "schema",
        "mixed_generation",
        "identity",
    ],
)
def test_unusable_remote_bundle_exposes_no_logical_feed(failure_kind):
    remote = _remote_module()
    bundle = build_bundle(_feed([_news()]))
    manifest = json.loads(bundle.manifest_bytes)
    target = manifest["artifacts"][0]
    target_path = target["path"]
    original = bundle.artifact_bytes[target["domain"]]
    overrides: dict[str, bytes] = {}
    failures: dict[str, object] = {}

    if failure_kind == "missing":
        failures[target_path] = 404
    elif failure_kind == "short":
        overrides[target_path] = original[:-1]
    elif failure_kind == "oversized":
        overrides[target_path] = original + b"x"
    elif failure_kind == "sha256":
        overrides[target_path] = bytes([original[0] ^ 1]) + original[1:]
    elif failure_kind == "schema":
        artifact = json.loads(original)
        artifact["schema_version"] = 2
        overrides[target_path] = canonical_bytes(artifact)
        target["size_bytes"] = len(overrides[target_path])
        target["sha256"] = canonical_sha256(overrides[target_path])
    elif failure_kind == "mixed_generation":
        other = build_bundle(_feed([_news("item-2")]))
        overrides[target_path] = other.artifact_bytes[target["domain"]]
        target["size_bytes"] = len(overrides[target_path])
        target["sha256"] = canonical_sha256(overrides[target_path])
    elif failure_kind == "identity":
        manifest["content_digest"] = "0" * 64
    manifest_bytes, artifacts = _payloads(bundle, manifest, overrides)
    calls: list[str] = []
    with (
        _client_for_payloads(
            remote,
            calls,
            manifest_bytes,
            artifacts,
            failures=failures,
        ) as client,
        pytest.raises(remote.FeedRemoteError),
    ):
        remote.consume_published_feed(client=client)


def test_identity_valid_failure_bundle_is_not_consumable():
    remote = _remote_module()
    feed = _feed()
    feed["pipeline"]["status"] = "failure"
    feed["content_digest"], feed["run_id"] = recompute_feed_identity(feed)
    bundle = build_bundle(feed)
    calls: list[str] = []
    with (
        _client_for_bundle(bundle, remote, calls) as client,
        pytest.raises(
            remote.FeedRemoteError, match="pipeline.status=failure: Feed is not consumable"
        ),
    ):
        remote.consume_published_feed(client=client)
    assert len(calls) == 9


@pytest.mark.parametrize("status", [429, 500])
def test_http_and_rate_limit_failures_are_typed(status):
    remote = _remote_module()
    bundle = build_bundle(_feed())
    calls: list[str] = []
    with (
        _client_for_bundle(
            bundle, remote, calls, failures={"feed-manifest.json": status}
        ) as client,
        pytest.raises(remote.FeedRemoteError, match=f"HTTP {status}"),
    ):
        remote.consume_published_feed(client=client)


def test_timeout_is_typed_and_stops_before_artifact_request():
    remote = _remote_module()
    bundle = build_bundle(_feed())
    calls: list[str] = []
    timeout = httpx.ReadTimeout("timed out")
    with (
        _client_for_bundle(
            bundle, remote, calls, failures={"feed-manifest.json": timeout}
        ) as client,
        pytest.raises(remote.FeedRemoteError, match="ReadTimeout"),
    ):
        remote.consume_published_feed(client=client)
    assert calls == [remote._raw_url("feed-manifest.json")]


@pytest.mark.parametrize(
    ("content_length", "message"),
    [("1048577", "response exceeds 1048576 bytes"), ("invalid", "invalid Content-Length")],
)
def test_manifest_content_length_preserves_precise_failure(content_length, message):
    remote = _remote_module()

    def handler(request):
        return httpx.Response(200, headers={"Content-Length": content_length}, request=request)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(remote.FeedRemoteError, match=message),
    ):
        remote.consume_published_feed(client=client)


def test_streamed_response_size_limit_stops_and_closes_without_content_length():
    remote = _remote_module()
    closed = False

    class OversizedStream(httpx.SyncByteStream):
        def __iter__(self):
            yield b"x" * 1048577
            pytest.fail("oversized response must stop before another chunk")

        def close(self):
            nonlocal closed
            closed = True

    def handler(request):
        return httpx.Response(200, stream=OversizedStream(), request=request)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(remote.FeedRemoteError, match="response exceeds 1048576 bytes"),
    ):
        remote.consume_published_feed(client=client)
    assert closed


def test_temporary_remote_product_root_is_removed(monkeypatch):
    remote = _remote_module()
    bundle = build_bundle(_feed())
    calls: list[str] = []
    real_temporary_directory = remote.tempfile.TemporaryDirectory
    created: list[Path] = []

    class TrackingTemporaryDirectory:
        def __init__(self, *args, **kwargs):
            self._delegate = real_temporary_directory(*args, **kwargs)

        def __enter__(self):
            path = Path(self._delegate.__enter__())
            created.append(path)
            return str(path)

        def __exit__(self, *args):
            return self._delegate.__exit__(*args)

    monkeypatch.setattr(remote.tempfile, "TemporaryDirectory", TrackingTemporaryDirectory)
    with _client_for_bundle(bundle, remote, calls) as client:
        assert remote.consume_published_feed(client=client)["run_id"] == bundle.run_id

    assert created and not created[0].exists()


@pytest.mark.parametrize("failure_at", ["directory", "write"])
def test_temporary_storage_failure_is_typed_and_cleans_up(monkeypatch, tmp_path, failure_at):
    remote = _remote_module()
    bundle = build_bundle(_feed())
    calls: list[str] = []
    monkeypatch.setattr(remote.tempfile, "tempdir", str(tmp_path))

    def unavailable(*_args, **_kwargs):
        raise OSError("disk unavailable")

    if failure_at == "directory":
        monkeypatch.setattr(remote.tempfile, "mkdtemp", unavailable)
    else:
        monkeypatch.setattr(Path, "write_bytes", unavailable)

    with (
        _client_for_bundle(bundle, remote, calls) as client,
        pytest.raises(remote.FeedRemoteError, match="Feed temporary storage: disk unavailable"),
    ):
        remote.consume_published_feed(client=client)

    assert list(tmp_path.iterdir()) == []


def _file_snapshot(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()
    }


def test_remote_failure_has_no_local_fallback_or_persistent_feed_mutation(monkeypatch):
    remote = _remote_module()
    source = inspect.getsource(remote)
    assert "run_feed" not in source
    assert "follow_the_money.providers" not in source
    assert "feed.deployment" not in source

    bundle = build_bundle(_feed())
    target_path = bundle.manifest["artifacts"][0]["path"]
    calls: list[str] = []
    load_called = False

    def fail_if_loaded(*_args, **_kwargs):
        nonlocal load_called
        load_called = True
        raise AssertionError("remote failure must not fall back to local Feed loading")

    monkeypatch.setattr(remote, "load_feed", fail_if_loaded)
    before = {
        "feeds": _file_snapshot(REPO_ROOT / "feeds"),
        "state": _file_snapshot(REPO_ROOT / ".feed-state"),
    }
    with (
        _client_for_bundle(bundle, remote, calls, failures={target_path: 503}) as client,
        pytest.raises(remote.FeedRemoteError, match="HTTP 503"),
    ):
        remote.consume_published_feed(client=client)
    after = {
        "feeds": _file_snapshot(REPO_ROOT / "feeds"),
        "state": _file_snapshot(REPO_ROOT / ".feed-state"),
    }

    assert not load_called
    assert after == before
