from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

import mountainash_rules_babel as babel
from mountainash_rules_babel.registry import registry

app = typer.Typer(name="babel", help="Mountain Ash Rules Babel — translate decision logic between formats.")


@app.command()
def formats() -> None:
    """List available import/export formats."""
    exporters = registry.list_exporters()
    importers = registry.list_importers()

    typer.echo("Exporters:")
    for name in exporters:
        exp = registry.get_exporter(name)
        typer.echo(f"  {name} ({exp.file_extension})")

    typer.echo("\nImporters:")
    for name in importers:
        imp = registry.get_importer(name)
        typer.echo(f"  {name} ({', '.join(imp.file_extensions)})")

    decomposers = registry.list_decomposers()
    if decomposers:
        typer.echo("\nDecomposers:")
        for name in decomposers:
            typer.echo(f"  {name}")

    validators = registry.list_validators()
    if validators:
        typer.echo("\nValidators:")
        for name in validators:
            typer.echo(f"  {name}")


@app.command(name="export")
def export_cmd(
    format: str = typer.Option(..., "--format", "-f", help="Output format name"),
    input: Path = typer.Option(..., "--input", "-i", help="Input CSV file"),
    output: Path = typer.Option(..., "--output", "-o", help="Output file path"),
    dim: list[str] = typer.Option([], "--dim", "-d", help="Dimension column names"),
) -> None:
    """Export a Lattice to an external format."""
    lattice = babel.import_lattice(
        input,
        format="csv",
        dimension_columns=dim if dim else None,
    )
    babel.export_lattice(lattice, format, path=output)
    typer.echo(f"Exported {lattice.count} rows to {output} ({format})")


@app.command(name="import")
def import_cmd(
    input: Path = typer.Option(..., "--input", "-i", help="Input file path"),
    format: Optional[str] = typer.Option(None, "--format", "-f", help="Input format (inferred if omitted)"),
    dim: list[str] = typer.Option([], "--dim", "-d", help="Dimension column names"),
) -> None:
    """Import an external format and show stats."""
    lattice = babel.import_lattice(
        input,
        format=format,
        dimension_columns=dim if dim else None,
    )
    typer.echo(f"Imported {lattice.count} rows")
    typer.echo(f"Dimensions: {[d.dimension_name for d in lattice.metadata.dimensions]}")
    typer.echo(f"Aggregates: {[a.column_name for a in lattice.aggregates]}")


@app.command(name="validate")
def validate_cmd(
    input: Path = typer.Option(..., "--input", "-i", help="Input file path"),
    checks: Optional[str] = typer.Option(None, "--checks", "-c", help="Comma-separated validator names"),
    dim: list[str] = typer.Option([], "--dim", "-d", help="Dimension column names"),
) -> None:
    """Run validation checks on a Lattice."""
    lattice = babel.import_lattice(
        input,
        format="csv",
        dimension_columns=dim if dim else None,
    )
    check_list = checks.split(",") if checks else None
    report = babel.validate(lattice, checks=check_list)
    typer.echo(f"Valid: {report.is_valid}")
    for issue in report.issues:
        typer.echo(f"  [{issue.severity}] {issue.category}: {issue.message}")


if __name__ == "__main__":
    app()
