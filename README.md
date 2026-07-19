# mountainash-rules-babel

![Python](https://img.shields.io/badge/python-3.12-blue) ![License](https://img.shields.io/badge/license-Apache--2.0-green)

Translate decision logic between formats. Babel moves [mountainash-rules](https://github.com/mountainash-io/mountainash-rules) lattices in and out of external decision formats — CSV (with a metadata manifest sidecar) and DMN today — with validation that round trips are lossless.

## Quick Start

```python
import mountainash_rules_babel as babel

# Export a lattice (from AccumulatorEngine.build() or built by hand)
babel.export_lattice(lattice, "csv", path="rules.csv")
# -> rules.csv + rules.manifest.yaml (dimensions + aggregates)

# Re-import: the sidecar restores metadata and aggregates automatically
lattice = babel.import_lattice("rules.csv")

# DMN export (hitPolicy comes from the lattice's metadata)
babel.export_lattice(lattice, "dmn", path="rules.dmn")

# Validate a CSV round trip is lossless
report = babel.validate(lattice, checks=["round_trip"])
assert report.is_valid
```

Or from the command line:

```bash
babel formats                                  # list exporters/importers/validators
babel export -f dmn -i rules.csv -o rules.dmn
babel import -i rules.csv
babel validate -i rules.csv -c round_trip
```

## The schema contract

Lattices out of `AccumulatorEngine.build()` are **composed**: each row is a combination of rules whose authoritative values live in coalesced (`co_*`) and aggregate (`__agg_*`) columns, while the plain columns are stale copies from an anchor rule. Babel's exporters normalise every lattice through a single resolver so files always carry the authoritative values under flat column names — and imports always come back **flat** (recombination belongs to the engine, not the file format). Don't-care values are empty cells in files and typed sentinels in frames.

The full contract — column taxonomy, sentinel encoding, sidecar manifest, DMN fail-closed rules — is documented in [`docs/lattice-schema.md`](docs/lattice-schema.md).

## Formats

| Format | Import | Export | Notes |
|---|---|---|---|
| CSV | ✓ | ✓ | manifest sidecar (`<stem>.manifest.yaml`) restores metadata + aggregates |
| DMN 1.3 | planned | ✓ | hitPolicy from metadata; UNIQUE on composed lattices fails closed unless `assume_unique=True` |
| GoRules JDM | planned | planned | optional extra: `jdm` |
| flagd / OpenFeature | planned | planned | optional extra: `flagd` |

Validators: `round_trip` (real for CSV), `conflicts` / `coverage` / `orphans` (fail-closed until implemented — they report invalid rather than silently passing).

## Installation

```bash
git clone https://github.com/mountainash-io/mountainash-rules-babel.git
cd mountainash-rules-babel
hatch env create
```

Requires a sibling checkout of `mountainash-rules` (see `hatch.toml`). After changing that repo, run `hatch env prune` here to pick up the new code.

## Development

| Command | Description |
|---|---|
| `hatch run test:test-quick` | Run tests |
| `hatch run test:test-cov` | Tests with coverage |
| `hatch run test:test-target tests/path.py` | Run specific tests |
| `hatch run ruff:check` / `ruff:fix` | Lint / auto-fix |

See [CLAUDE.md](CLAUDE.md) for architecture details.

## Mountain Ash Ecosystem

Part of the [Mountain Ash](https://github.com/mountainash-io) data framework ecosystem.

## License

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE) for details.
