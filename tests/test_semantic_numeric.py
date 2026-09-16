"""Focused tests for the bounded ECO-125 numeric fact primitives."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from decimal import ROUND_DOWN, Inexact, localcontext

import pytest

from follow_the_money.schema import SchemaError
from follow_the_money.semantic import (  # pyright: ignore[reportMissingImports]
    DerivedNumericFact,
    MeasuredNumericFact,
    add_canonical,
    canonicalize_numeric,
    derive_subtraction,
    scale_power_of_ten,
    subtract_canonical,
)


def test_measured_numeric_fact_is_bounded_numeric_only_and_immutable():
    fact = MeasuredNumericFact.from_raw(
        name="sec.reported_amount",
        raw_value="1.2300",
        unit="shares",
        source_fields=("sshPrnamt",),
        nonnegative=True,
    )

    assert fact.name == "sec.reported_amount"
    assert fact.value == "1.23"
    assert fact.unit == "shares"
    assert fact.source_fields == ("sshPrnamt",)
    assert {field.name for field in fields(fact)} == {"name", "value", "unit", "source_fields"}
    with pytest.raises(FrozenInstanceError):
        fact.__setattr__("value", "2")

    for raw_value in ("-1", "NaN", "Infinity", "1e99", "1" * 25, "1."):
        with pytest.raises(SchemaError):
            MeasuredNumericFact.from_raw(
                name="sec.value",
                raw_value=raw_value,
                unit="usd_thousands",
                source_fields=("value",),
                nonnegative=True,
            )

    with pytest.raises(SchemaError, match="negative zero"):
        MeasuredNumericFact.from_canonical(
            name="sec.value",
            value="-0",
            unit="usd_thousands",
            source_fields=("value",),
        )
    unexpected = {"identity": "not-a-numeric-concern"}
    with pytest.raises(TypeError):
        MeasuredNumericFact(
            name="x",
            value="1",
            unit="shares",
            source_fields=("field",),
            **unexpected,
        )


def test_owned_arithmetic_ignores_ambient_state_and_fails_closed_on_contract_overflow():
    with localcontext() as ambient:
        ambient.prec = 6
        ambient.rounding = ROUND_DOWN
        ambient.flags[Inexact] = True
        ambient.traps[Inexact] = True
        before = (ambient.prec, ambient.rounding, ambient.flags[Inexact], ambient.traps[Inexact])

        assert canonicalize_numeric("123456789.123456789", where="value") == "123456789.123456789"
        assert (
            add_canonical(
                "123456789.123456789",
                "0.876543211",
                where="sum",
            )
            == "123456790"
        )
        assert (
            subtract_canonical(
                "123456789.123456789",
                "0.876543211",
                where="difference",
            )
            == "123456788.246913578"
        )
        assert (
            scale_power_of_ten("123456789.123456789", -3, where="scaled") == "123456.789123456789"
        )
        after = (ambient.prec, ambient.rounding, ambient.flags[Inexact], ambient.traps[Inexact])
        assert after == before

        with pytest.raises(SchemaError):
            add_canonical("1000000000000000000", "1", where="overflow")
        with pytest.raises(SchemaError):
            scale_power_of_ten("1000000000000000000", 1, where="overflow")


def test_derived_numeric_fact_keeps_ordered_direct_inputs_and_supports_chains():
    long = MeasuredNumericFact.from_raw(
        name="cftc.noncommercial_long",
        raw_value="12",
        unit="contracts",
        source_fields=("noncomm_positions_long_all",),
        nonnegative=True,
    )
    short = MeasuredNumericFact.from_raw(
        name="cftc.noncommercial_short",
        raw_value="5",
        unit="contracts",
        source_fields=("noncomm_positions_short_all",),
        nonnegative=True,
    )
    net = derive_subtraction(name="cftc.net_noncommercial", minuend=long, subtrahend=short)

    assert isinstance(net, DerivedNumericFact)
    assert net.value == "7"
    assert net.unit == "contracts"
    assert net.derivation.operation == "subtract"
    assert net.derivation.inputs == (long, short)
    assert net.derivation.inputs[0] is long
    assert net.derivation.inputs[1] is short
    assert not hasattr(net, "formula_id")
    assert not hasattr(net.derivation, "json_path")

    prior_net = derive_subtraction(
        name="cftc.net_delta",
        minuend=net,
        subtrahend=MeasuredNumericFact.from_raw(
            name="cftc.previous_net_noncommercial",
            raw_value="2",
            unit="contracts",
            source_fields=("previous.net_noncommercial",),
            nonnegative=False,
        ),
    )
    assert prior_net.value == "5"
    assert prior_net.derivation.inputs[0] is net
    with pytest.raises(FrozenInstanceError):
        net.__setattr__("derivation", prior_net.derivation)
    with pytest.raises(SchemaError, match="unit"):
        derive_subtraction(
            name="bad",
            minuend=long,
            subtrahend=MeasuredNumericFact.from_raw(
                name="usd",
                raw_value="1",
                unit="usd",
                source_fields=("value",),
                nonnegative=True,
            ),
        )
