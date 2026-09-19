# Lattice transport contract

Babel supports two deliberately separate transport fidelities. It does not
reconstruct exact state from a table and it does not silently flatten an exact
artifact.

## Flat values: CSV and DMN

CSV sidecars declare inspection-only flat values:

```yaml
fidelity: flat_values
dimensions: ...
aggregates:
  - column_name: amount
    operation: sum
```

Those are the only fields in a newly emitted sidecar. Babel accepts the
historical untagged `{dimensions, aggregates}` shape for flat inspection, but
rejects unknown fields, unknown fidelity, and native discriminators. An
`AggregateSpec` intentionally contains only its source column and operation;
a CSV value cannot establish output scalar type, timezone, numeric semantics,
or exact-native eligibility.

CSV and DMN accept only a `Lattice` whose public `artifact_kind` is absent
(flat inspection data). An `exact_cells` artifact fails at the adapter boundary
even when its predicates happen to look scalar. There is no `assume_unique`
bypass, composition marker, prime/rank export, or native-to-flat projection.

At the CSV boundary, sentinel conversion is metadata-directed: only declared
dimension value columns are blanked, including both range endpoints. Output
columns are never scanned for sentinels, so an integer output value of
`-999999999` remains that value. Boolean null dimensions remain null; nested
set columns are not a CSV interchange shape and retain Polars' explicit
unsupported nested-CSV failure.

## Native snapshots: Python API

The explicit `native` format transports a complete Rules snapshot directory.
It delegates atomically to `Lattice.save` and `Lattice.load`; Babel neither
rewrites amount tables nor creates a wrapper manifest, archive, bindings,
sources, scopes, predicates, or geometry.

```python
from mountainash_rules import ExactLimits
import mountainash_rules_babel as babel

# The caller must supply a complete, explicit ExactLimits instance.
limits: ExactLimits = configured_limits
babel.export_lattice(lattice, "native", path="pricing.snapshot", limits=limits)
restored = babel.import_lattice("pricing.snapshot", format="native", limits=limits)
```

Native export requires `lattice.artifact_kind == "exact_cells"`. Native import
uses Rules' bounded loader and rejects a legacy inspection snapshot. Native
byte export is unsupported because no archive format is defined. Omitted
import format continues to infer only ordinary file extensions; a directory is
never inferred as native.

`round_trip` validation is fidelity-aware. Flat CSV validation performs its
structural table comparison only on flat values. Native validation uses Rules
save/load under the caller's limits and compares public artifact, partition,
resolved metadata, aggregate, and binding identity. `export_lattice(...,
validate=True)` forwards its real format and limits; for native output it
validates the directory just written.

Native CLI support is deferred. The existing command-line CSV/DMN flows remain
flat-only; native transport is available through the Python API above.
