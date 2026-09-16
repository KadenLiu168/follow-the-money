"""Bounded, deterministic numeric primitives for Producer-internal facts."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from decimal import (
    Clamped,
    Context,
    Decimal,
    DecimalException,
    DivisionByZero,
    Inexact,
    InvalidOperation,
    Overflow,
    Rounded,
    Subnormal,
    Underflow,
    localcontext,
)
from typing import Any, Literal

from ..schema import SchemaError

_RAW_NUMERIC = re.compile(r"^[+-]?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$")
_CANONICAL_NUMERIC = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
_MAX_BYTES = 64
_MAX_SIGNIFICANT_DIGITS = 24
_MAX_EXPONENT = 12
_ARITHMETIC_PRECISION = 128


def validate_numeric_token(token: str, *, where: str) -> None:
    """Validate a bounded raw numeric token before Decimal construction."""
    if not _RAW_NUMERIC.match(token):
        raise SchemaError(f"{where}: invalid raw numeric token {token!r}")
    mantissa = token.lstrip("+-")
    exponent = 0
    if "e" in mantissa.lower():
        mantissa, _, exp_part = mantissa.lower().partition("e")
        try:
            exponent = int(exp_part)
        except ValueError as exc:
            raise SchemaError(f"{where}: invalid raw numeric token {token!r}") from exc
    if exponent < -_MAX_EXPONENT or exponent > _MAX_EXPONENT:
        raise SchemaError(f"{where}: exponent out of range [-12, 12]: {token!r}")
    digits = mantissa.replace(".", "").lstrip("0") or "0"
    if len(digits) > _MAX_SIGNIFICANT_DIGITS:
        raise SchemaError(f"{where}: more than 24 significant digits: {token!r}")
    if len(token) > _MAX_BYTES:
        raise SchemaError(f"{where}: token longer than 64 bytes: {token!r}")


def validate_canonical_numeric(value: str, *, where: str) -> None:
    """Validate a bounded persisted canonical plain decimal string."""
    if not _CANONICAL_NUMERIC.match(value):
        raise SchemaError(f"{where}: not canonical plain decimal: {value!r}")
    if value.startswith("-"):
        digits = value[1:].replace(".", "").lstrip("0")
        if digits == "":
            raise SchemaError(f"{where}: negative zero is forbidden: {value!r}")
    if len(value) > _MAX_BYTES:
        raise SchemaError(f"{where}: canonical value longer than 64 bytes")
    body = value.lstrip("-")
    digits = body.replace(".", "").lstrip("0") or "0"
    if len(digits) > _MAX_SIGNIFICANT_DIGITS:
        raise SchemaError(f"{where}: more than 24 significant digits: {value!r}")
    int_part = body.split(".")[0].lstrip("0") or "0"
    if len(int_part) > 19 or (len(int_part) == 19 and int_part > "1000000000000000000"):
        raise SchemaError(f"{where}: magnitude exceeds 10^18: {value!r}")


def _canonical_from_decimal(number: Decimal, *, where: str, nonnegative: bool = False) -> str:
    if not number.is_finite() or (nonnegative and number < 0):
        raise SchemaError(f"{where}: numeric value is invalid")
    normalized = format(number, "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    if normalized in {"", "-0"}:
        normalized = "0"
    validate_canonical_numeric(normalized, where=where)
    return normalized


def canonicalize_numeric(value: Any, *, where: str, nonnegative: bool = False) -> str:
    """Parse and normalize one bounded raw numeric value without ambient state."""
    text = str(value).strip()
    validate_numeric_token(text, where=where)
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise SchemaError(f"{where}: invalid decimal") from exc
    return _canonical_from_decimal(number, where=where, nonnegative=nonnegative)


def canonicalize_canonical(value: str, *, where: str, nonnegative: bool = False) -> str:
    """Normalize an already canonical value while retaining its guard errors."""
    validate_canonical_numeric(value, where=where)
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise SchemaError(f"{where}: numeric value is invalid") from exc
    return _canonical_from_decimal(number, where=where, nonnegative=nonnegative)


def _owned_context() -> Context:
    context = Context(prec=_ARITHMETIC_PRECISION)
    for signal in (
        Clamped,
        DivisionByZero,
        Inexact,
        InvalidOperation,
        Overflow,
        Rounded,
        Subnormal,
        Underflow,
    ):
        context.traps[signal] = True
    return context


def _exact_operation(operation: Callable[[], Decimal], *, where: str) -> Decimal:
    with localcontext(_owned_context()) as context:
        try:
            result = operation()
        except (DecimalException, ValueError) as exc:
            raise SchemaError(f"{where}: arithmetic result is invalid") from exc
        if any(
            context.flags[signal] for signal in (Inexact, Rounded, Overflow, Underflow, Clamped)
        ):
            raise SchemaError(f"{where}: arithmetic result is inexact")
    return result


def _canonical_operand(value: str, *, where: str) -> Decimal:
    canonicalize_canonical(value, where=where)
    return Decimal(value)


def add_canonical(left: str, right: str, *, where: str, nonnegative: bool = False) -> str:
    left_number = _canonical_operand(left, where=f"{where}.left")
    right_number = _canonical_operand(right, where=f"{where}.right")
    result = _exact_operation(lambda: left_number + right_number, where=where)
    return _canonical_from_decimal(result, where=where, nonnegative=nonnegative)


def subtract_canonical(left: str, right: str, *, where: str) -> str:
    left_number = _canonical_operand(left, where=f"{where}.minuend")
    right_number = _canonical_operand(right, where=f"{where}.subtrahend")
    result = _exact_operation(lambda: left_number - right_number, where=where)
    return _canonical_from_decimal(result, where=where)


def scale_power_of_ten(value: str, power: int, *, where: str, nonnegative: bool = False) -> str:
    number = _canonical_operand(value, where=where)
    result = _exact_operation(lambda: number.scaleb(power), where=where)
    return _canonical_from_decimal(result, where=where, nonnegative=nonnegative)


@dataclass(frozen=True, slots=True)
class MeasuredNumericFact:
    """Provider-local measured numeric value with bounded source support."""

    name: str
    value: str
    unit: str
    source_fields: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise SchemaError("numeric fact name is required")
        if not isinstance(self.unit, str) or not self.unit.strip():
            raise SchemaError("numeric fact unit is required")
        if isinstance(self.source_fields, str):
            raise SchemaError("numeric fact source_fields must be a tuple of field names")
        fields = tuple(self.source_fields)
        if not fields or any(not isinstance(field, str) or not field.strip() for field in fields):
            raise SchemaError("numeric fact source_fields are required")
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "unit", self.unit.strip())
        object.__setattr__(self, "source_fields", fields)
        object.__setattr__(
            self,
            "value",
            canonicalize_canonical(self.value, where=f"{self.name}.value"),
        )

    @classmethod
    def from_raw(
        cls,
        *,
        name: str,
        raw_value: object,
        unit: str,
        source_fields: tuple[str, ...],
        nonnegative: bool = False,
    ) -> MeasuredNumericFact:
        value = canonicalize_numeric(raw_value, where=f"{name}.value", nonnegative=nonnegative)
        return cls(name=name, value=value, unit=unit, source_fields=source_fields)

    @classmethod
    def from_canonical(
        cls,
        *,
        name: str,
        value: str,
        unit: str,
        source_fields: tuple[str, ...],
        nonnegative: bool = False,
    ) -> MeasuredNumericFact:
        canonical = canonicalize_canonical(value, where=f"{name}.value", nonnegative=nonnegative)
        return cls(name=name, value=canonical, unit=unit, source_fields=source_fields)


@dataclass(frozen=True, slots=True)
class NumericDerivation:
    """Immediate execution record for the only shared operation: subtraction."""

    operation: Literal["subtract"]
    inputs: tuple[MeasuredNumericFact | DerivedNumericFact, ...]

    def __post_init__(self) -> None:
        if self.operation != "subtract":
            raise SchemaError("unsupported numeric derivation operation")
        inputs = tuple(self.inputs)
        if len(inputs) != 2 or not all(
            isinstance(value, (MeasuredNumericFact, DerivedNumericFact)) for value in inputs
        ):
            raise SchemaError("subtraction derivation requires two numeric fact inputs")
        object.__setattr__(self, "inputs", inputs)


@dataclass(frozen=True, slots=True)
class DerivedNumericFact:
    """Numeric result with direct immutable inputs for immediate provenance."""

    name: str
    value: str
    unit: str
    derivation: NumericDerivation

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise SchemaError("derived numeric fact name is required")
        if not isinstance(self.unit, str) or not self.unit.strip():
            raise SchemaError("derived numeric fact unit is required")
        if not isinstance(self.derivation, NumericDerivation):
            raise SchemaError("derived numeric fact derivation is required")
        if not isinstance(self.value, str):
            raise SchemaError("derived numeric fact value must be canonical")
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "unit", self.unit.strip())
        object.__setattr__(
            self,
            "value",
            canonicalize_canonical(self.value, where=f"{self.name}.value"),
        )


def derive_subtraction(
    *,
    name: str,
    minuend: MeasuredNumericFact | DerivedNumericFact,
    subtrahend: MeasuredNumericFact | DerivedNumericFact,
) -> DerivedNumericFact:
    """Execute and record ``minuend - subtrahend`` using direct fact objects."""
    if not isinstance(minuend, (MeasuredNumericFact, DerivedNumericFact)):
        raise SchemaError("subtraction minuend must be a numeric fact")
    if not isinstance(subtrahend, (MeasuredNumericFact, DerivedNumericFact)):
        raise SchemaError("subtraction subtrahend must be a numeric fact")
    if minuend.unit != subtrahend.unit:
        raise SchemaError(f"{name}: subtraction requires equal units")
    value = subtract_canonical(minuend.value, subtrahend.value, where=f"{name}.value")
    return DerivedNumericFact(
        name=name,
        value=value,
        unit=minuend.unit,
        derivation=NumericDerivation("subtract", (minuend, subtrahend)),
    )
