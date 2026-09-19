# mountainash-rules-babel

![Python](https://img.shields.io/badge/python-3.12-blue) ![License](https://img.shields.io/badge/license-Apache--2.0-green)

Translate Mountain Ash Rules lattices between declared transport fidelities.
CSV and DMN carry inspection-only flat values. The explicit Python-only native
format carries a complete bounded Rules snapshot without flattening it.

## Flat CSV and DMN

```python
import mountainash_rules_babel as babel

babel.export_lattice(flat_lattice, "csv", path="rules.csv")
# writes rules.csv and rules.manifest.yaml
restored_flat = babel.import_lattice("rules.csv")
babel.export_lattice(restored_flat, "dmn", path="rules.dmn")
```

New CSV sidecars contain exactly `fidelity: flat_values`, `dimensions`, and
`aggregates`. Historical untagged two-field sidecars remain readable as flat
inspection data. CSV sentinel handling applies only to declared dimension
columns (including range endpoints), never output columns.

CSV and DMN reject `exact_cells` artifacts. Babel does not infer exact-native
eligibility from flat data, compose a flat table, or perform a lossy
native-to-flat projection.

## Native Python transport

```python
from mountainash_rules import ExactLimits
import mountainash_rules_babel as babel

limits: ExactLimits = configured_complete_limits
babel.export_lattice(lattice, "native", path="pricing.snapshot", limits=limits)
restored = babel.import_lattice("pricing.snapshot", format="native", limits=limits)
```

`native` requires a complete explicit `ExactLimits`, an exact-native lattice,
and a directory path. It delegates persistence to Rules and preserves the
complete snapshot. Native byte export, extension inference for directories,
and legacy-as-native import all fail explicitly. `validate=True` validates the
actual native directory through Rules load rather than applying CSV checks.

Native CLI support is deferred. The existing command-line commands remain for
flat CSV/DMN workflows:

```bash
babel formats
babel export -f dmn -i rules.csv -o rules.dmn
babel import -i rules.csv
babel validate -i rules.csv -c round_trip
```

## Validation

`round_trip` validates flat CSV structurally only for flat lattices. Native
round trips use bounded Rules save/load and compare public artifact, partition,
resolved metadata, aggregate, and binding identity. `conflicts`, `coverage`,
and `orphans` remain fail-closed until implemented.

## Installation

```bash
git clone https://github.com/mountainash-io/mountainash-rules-babel.git
cd mountainash-rules-babel
hatch env create
```

Requires a sibling checkout of `mountainash-rules` (see `hatch.toml`). After
changing that repository, run `hatch env prune` here to pick up the new code.

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

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
