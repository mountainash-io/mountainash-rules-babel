from mountainash_rules_babel.errors import (
    BabelError,
    DecompositionError,
    DependencyMissingError,
    ExportError,
    FormatNotFoundError,
    ImportError_,
    ValidationError,
)


def test_babel_error_is_base():
    assert issubclass(FormatNotFoundError, BabelError)
    assert issubclass(ImportError_, BabelError)
    assert issubclass(ExportError, BabelError)
    assert issubclass(DecompositionError, BabelError)
    assert issubclass(ValidationError, BabelError)
    assert issubclass(DependencyMissingError, BabelError)


def test_dependency_missing_is_import_error():
    assert issubclass(DependencyMissingError, ImportError)


def test_format_not_found_includes_available():
    err = FormatNotFoundError("csv", available=["dmn", "jdm"])
    assert "csv" in str(err)
    assert "dmn" in str(err)
    assert "jdm" in str(err)


def test_validation_error_carries_report():
    from mountainash_rules_babel.validators.base import ValidationReport

    report = ValidationReport(is_valid=False, issues=[])
    err = ValidationError("validation failed", report=report)
    assert err.report is report
