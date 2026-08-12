"""Single-model OpenAI Responses API adapter (task 7.1/7.2).

Design section 9:

- One configured compatible model for all four passes; ``store: false``,
  no provider-side conversation state, no tools/retrieval/files/URLs.
- Typed failure state machine: connection/timeout/HTTP-408|409|429|5xx are
  transient (at most one same-model retry when full timeout + reserve fits);
  400|401|403|404|422, refusal, incomplete, context/capability, structure/
  reference/capacity/content, cancellation are non-retryable.
- Pinned zero reasoning; nonzero/missing ``output_tokens_details.reasoning_tokens``
  is typed ``unexpected_reasoning_usage`` and fails non-retryably.
- Per-attempt timeouts 30/45/45/30s; output-token caps 72k/72k/72k/56k;
  response caps 64/64/64/48 KiB; at most two attempts per invocation;
  resolver/analyst concurrency 4 with stable joins.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from .unicode import utf8_byte_length

PASS_LIMITS = {
    "resolver": {"timeout": 30, "max_output_tokens": 72000, "max_response_bytes": 64 * 1024},
    "analyst": {"timeout": 45, "max_output_tokens": 72000, "max_response_bytes": 64 * 1024},
    "editor": {"timeout": 45, "max_output_tokens": 72000, "max_response_bytes": 64 * 1024},
    "audit": {"timeout": 30, "max_output_tokens": 56000, "max_response_bytes": 48 * 1024},
    "language-audit": {"timeout": 30, "max_output_tokens": 56000, "max_response_bytes": 48 * 1024},
}

TRANSIENT_HTTP = {408, 409, 429}
TRANSIENT_5XX = range(500, 600)
NON_RETRYABLE_HTTP = {400, 401, 403, 404, 422}


class LlmError(ValueError):
    """Typed LLM pass failure."""


@dataclass(frozen=True)
class LlmOutcome:
    status: str  # success | refused | incomplete | timeout | transient_failure | non_retryable | exhaustion
    data: Any = None
    attempts: int = 1
    error: str | None = None
    retried: bool = False


@dataclass
class FakeClientResponse:
    status: str = "completed"
    output_text: str = "{}"
    model: str = "gpt-test"
    reasoning_tokens: int = 0
    usage: dict[str, int] = field(default_factory=lambda: {"input_tokens": 10, "output_tokens": 5})
    refusal_reason: str | None = None

    def __post_init__(self) -> None:
        from types import SimpleNamespace

        self.output_tokens_details = SimpleNamespace(reasoning_tokens=self.reasoning_tokens)


class ResponsesAdapter:
    """OpenAI Responses API adapter with injected client (fake for tests)."""

    def __init__(self, *, model: str, client: Any, store: bool = False) -> None:
        self.model = model
        self.client = client
        self.store = store

    def call(
        self,
        *,
        pass_name: str,
        prompt: str,
        response_schema: Mapping[str, Any],
        envelope: Mapping[str, Any],
        monotonic_deadline: float | None = None,
        monotonic_now: Callable[[], float] | None = None,
        reserve_seconds: float = 15.0,
    ) -> LlmOutcome:
        limits = PASS_LIMITS[pass_name]
        now = monotonic_now or (lambda: 0.0)
        attempts = 0
        last_error: str | None = None

        while attempts < 2:
            attempts += 1
            if monotonic_deadline is not None:
                remaining = monotonic_deadline - now()
                if remaining < limits["timeout"] + reserve_seconds:
                    return LlmOutcome(
                        status="timeout",
                        attempts=attempts,
                        error=f"attempt {attempts} cannot fit remaining deadline",
                    )
            try:
                response = self.client.responses.create(
                    model=self.model,
                    input=prompt,
                    store=self.store,
                    reasoning={"effort": None},
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": f"{pass_name.replace('-', '_')}_output",
                            "schema": dict(response_schema),
                            "strict": True,
                        }
                    },
                )
            except Exception as exc:  # noqa: BLE001 - transport boundary
                last_error = f"{exc.__class__.__name__}: {exc}"
                code = getattr(exc, "status_code", None)
                is_transport = isinstance(exc, (ConnectionError, TimeoutError, OSError))
                if code is None and is_transport:
                    # Connection failure / per-attempt timeout: transient.
                    if attempts < 2:
                        continue
                    return LlmOutcome(status="exhaustion", attempts=attempts, error=last_error)
                if isinstance(code, int) and (code in TRANSIENT_HTTP or code in TRANSIENT_5XX):
                    if attempts < 2:
                        continue
                    return LlmOutcome(status="exhaustion", attempts=attempts, error=last_error)
                return LlmOutcome(status="non_retryable", attempts=attempts, error=last_error)

            # Validate response object.
            if getattr(response, "status", "completed") == "refused":
                return LlmOutcome(status="refused", data=response, attempts=attempts)
            reasoning = _reasoning_tokens(response)
            if reasoning is None or reasoning != 0:
                return LlmOutcome(
                    status="non_retryable",
                    attempts=attempts,
                    error="unexpected_reasoning_usage: nonzero/missing reasoning tokens",
                )
            text = _output_text(response)
            if utf8_byte_length(text) > limits["max_response_bytes"]:
                return LlmOutcome(
                    status="non_retryable",
                    attempts=attempts,
                    error="response_capacity_exceeded",
                )
            return LlmOutcome(
                status="success", data=response, attempts=attempts, retried=attempts > 1
            )

        return LlmOutcome(status="exhaustion", attempts=attempts, error=last_error)


def _reasoning_tokens(response: Any) -> int | None:
    try:
        details = response.output_tokens_details
        if details is None:
            return None
        value = details.reasoning_tokens
        return value if isinstance(value, int) else None
    except AttributeError:
        return None


def _output_text(response: Any) -> str:
    try:
        return response.output_text
    except AttributeError:
        return ""


def invoke_pass(
    adapter: ResponsesAdapter,
    *,
    pass_name: str,
    prompt: str,
    response_schema: Mapping[str, Any],
    envelope: Mapping[str, Any],
    canonical_input: Mapping[str, Any],
    monotonic_deadline: float | None = None,
) -> LlmOutcome:
    """Invoke one pass and decode the structured response."""

    outcome = adapter.call(
        pass_name=pass_name,
        prompt=prompt,
        response_schema=response_schema,
        envelope=envelope,
        monotonic_deadline=monotonic_deadline,
    )
    if outcome.status != "success":
        return outcome
    from .schema import validate_against

    text = _output_text(outcome.data)
    try:
        import json

        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return LlmOutcome(
            status="non_retryable", attempts=outcome.attempts, error=f"invalid structure: {exc}"
        )
    schema_name = f"{pass_name}-output.schema.json"
    try:
        validate_against(schema_name, payload)
    except Exception as exc:  # noqa: BLE001
        return LlmOutcome(
            status="non_retryable",
            attempts=outcome.attempts,
            error=f"structure/reference failure: {exc}",
        )
    return LlmOutcome(
        status="success", data=payload, attempts=outcome.attempts, retried=outcome.retried
    )
