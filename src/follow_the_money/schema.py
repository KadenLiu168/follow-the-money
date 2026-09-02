"""JSON Schema 2020-12 loading and validation for repository contracts.

Schemas live in ``schemas/*.json`` and are the serialized contract authority.
Validation adds strict UTF-8/Unicode-scalar checks plus canonical reference to
the JSON Schema library.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from .unicode import UnicodeError_, validate_scalar_string

SCHEMA_ROOT = Path(__file__).resolve().parents[2] / "schemas"


class SchemaError(ValueError):
    """Raised when a repository object fails its JSON Schema contract."""


@lru_cache(maxsize=32)
def _load_validator(rel_path: str) -> Draft202012Validator:
    path = SCHEMA_ROOT / rel_path
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise SchemaError(f"cannot read schema {rel_path}: {exc}") from exc
    try:
        schema = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SchemaError(f"schema {rel_path} is not valid strict UTF-8 JSON: {exc}") from exc
    # Physical bundle schemas reuse the legacy item definitions. Register the
    # local legacy resource so validation never performs network resolution.
    registry = Registry()
    if rel_path != "feed.schema.json":
        feed_path = SCHEMA_ROOT / "feed.schema.json"
        try:
            feed_schema = json.loads(feed_path.read_text(encoding="utf-8"))
            feed_resource = Resource.from_contents(feed_schema)
            feed_id = feed_schema.get("$id")
            if isinstance(feed_id, str):
                registry = registry.with_resource(feed_id, feed_resource)
            registry = registry.with_resource(feed_path.as_uri(), feed_resource)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise SchemaError(f"cannot read schema feed.schema.json: {exc}") from exc
    validator = Draft202012Validator(schema, registry=registry)
    # Eagerly compile to fail fast on schema errors.
    validator.check_schema(schema)
    return validator


def validate_against(schema_rel: str, instance: object) -> None:
    """Validate ``instance`` against ``schemas/<schema_rel>``.

    Raises :class:`SchemaError` on the first validation error. The instance
    must already be a decoded Python object; string values are additionally
    checked for Unicode scalar validity.
    """

    def _check(v: object) -> None:
        if isinstance(v, str):
            validate_scalar_string(v)
        elif isinstance(v, dict):
            for k, item in v.items():
                _check(k)
                _check(item)
        elif isinstance(v, list):
            for item in v:
                _check(item)

    try:
        _check(instance)
        validator = _load_validator(schema_rel)
    except UnicodeError_ as exc:
        raise SchemaError(str(exc)) from exc
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        first = errors[0]
        path = "/".join(str(p) for p in first.path) or "<root>"
        raise SchemaError(f"{schema_rel} @ {path}: {first.message}")
