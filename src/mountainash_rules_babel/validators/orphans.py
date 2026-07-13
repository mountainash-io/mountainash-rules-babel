from __future__ import annotations

from mountainash_rules import Lattice

from mountainash_rules_babel.validators.base import ValidationIssue, ValidationReport


class OrphansValidator:
    name: str = "orphans"

    def validate(self, lattice: Lattice, **options) -> ValidationReport:
        return ValidationReport(
            is_valid=False,
            issues=[
                ValidationIssue(
                    severity="warning",
                    category="not_implemented",
                    message="orphans validator is not yet implemented",
                )
            ],
        )
