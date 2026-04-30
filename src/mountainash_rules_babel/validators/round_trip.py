from __future__ import annotations

from mountainash_utils_rules.lattice import Lattice

from mountainash_rules_babel.validators.base import ValidationIssue, ValidationReport


class RoundTripValidator:
    name: str = "round_trip"

    def validate(self, lattice: Lattice, **options) -> ValidationReport:
        return ValidationReport(
            is_valid=False,
            issues=[
                ValidationIssue(
                    severity="warning",
                    category="not_implemented",
                    message="round_trip validator is not yet implemented",
                )
            ],
        )
