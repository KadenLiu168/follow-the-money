"""Compatibility module for the bounded semantic numeric fact types."""

from .numeric import DerivedNumericFact, MeasuredNumericFact, NumericDerivation, derive_subtraction

__all__ = [
    "DerivedNumericFact",
    "MeasuredNumericFact",
    "NumericDerivation",
    "derive_subtraction",
]
