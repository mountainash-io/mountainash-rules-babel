"""Public-API fixture builder for native Babel transport tests."""

from __future__ import annotations

import mountainash_rules as rules


def limits() -> rules.ExactLimits:
    return rules.ExactLimits(
        language={
            "max_input_bytes": 100_000,
            "max_nesting": 64,
            "max_nfa_states": 4_096,
            "max_states": 4_096,
            "max_transitions": 65_536,
            "max_work": 1_000_000,
        },
        max_input_bytes=10_000_000,
        max_output_bytes=10_000_000,
        max_work=1_000_000_000,
        max_live_bytes=100_000_000,
        max_predicate_nodes=100_000,
        max_dfa_states=100_000,
        max_dfa_transitions=1_000_000,
        max_theory_states=1_000_000,
        max_regions=100_000,
        max_scopes=10_000,
        max_source_scope_edges=100_000,
        max_contributor_edges=100_000,
        max_word_rows=100_000,
        max_numeric_bits=100_000,
        max_witnesses=100_000,
    )


def _scalar(value: int) -> dict[str, str]:
    return rules.encode_scalar(value, rules.DataType.INT)


def _envelope(kind: str, payload: dict) -> dict:
    return rules.make_exact_envelope(kind, payload, limits=limits())


def build_exact_lattice():
    """Build a source-gated exact artifact with shared-source sum/max lineage."""
    predicate = _envelope(
        "predicate",
        {
            "schema_version": 1,
            "node": {
                "op": "interval",
                "field": "x",
                "lower": _scalar(0),
                "upper": _scalar(30),
                "lower_closed": True,
                "upper_closed": True,
            },
        },
    )
    domain = rules.DomainDefinition(
        schema_version=1,
        domain_id="pricing-domain",
        fields=[rules.DomainField(name="x", data_type="int")],
        predicate_id=predicate["id"],
    )
    routing = _envelope(
        "routing",
        {
            "schema_version": 1,
            "semantics": "exact-key-1",
            "key_dimensions": [],
            "partition_keys": [[]],
        },
    )
    profile = rules.ResolutionProfile(
        profile_id="quote",
        mode="resolve",
        output_fields=["amount.max", "amount.sum"],
        provenance="cell",
        dimensions=["x"],
        allow_dont_care=["x"],
        promise="allow_unresolved",
        on_unresolved="return",
    )
    sum_only_profile = rules.ResolutionProfile(
        profile_id="sum-only",
        mode="candidates",
        output_fields=["amount.sum"],
        provenance="contributors",
        dimensions=["x"],
        allow_dont_care=["x"],
        promise="candidate_only",
        on_unresolved=None,
    )
    contract = rules.ContextContract(
        schema_version=1,
        contract_id="consumer",
        domain_ref="pricing-domain",
        fields=[rules.ContextField(name="x", data_type="int", required=True)],
        profiles=[profile, sum_only_profile],
    )
    metadata = rules.DimensionsMetadata(
        dimensions=[
            rules.Dimension(
                dimension_name="x",
                data_type="int",
                match_strategy="range",
                range_min_field="lo",
                range_max_field="hi",
            )
        ],
        context_contracts=[contract],
    )
    aggregates = [
        rules.Aggregate(
            column_name="amount",
            operation="sum",
            output_name="amount.sum",
            data_type="int",
            numeric_semantics="numeric-1",
        ),
        rules.Aggregate(
            column_name="amount",
            operation="max",
            output_name="amount.max",
            data_type="int",
            numeric_semantics="numeric-1",
        ),
    ]
    partition = {"routing_id": routing["id"], "key_values": []}
    source_scope = rules.Scope(
        partition_refs=[partition],
        domain_refs=["pricing-domain"],
        profile_refs=[],
    )
    contract_scope = rules.Scope(
        partition_refs=[partition],
        domain_refs=["pricing-domain"],
        profile_refs=[
            {"contract_id": contract.contract_id, "profile_id": profile.profile_id},
            {
                "contract_id": contract.contract_id,
                "profile_id": sum_only_profile.profile_id,
            },
        ],
    )
    profile_scope = rules.Scope(
        partition_refs=[partition],
        domain_refs=["pricing-domain"],
        profile_refs=[
            {"contract_id": contract.contract_id, "profile_id": profile.profile_id}
        ],
    )
    diagnostics = [
        rules.DiagnosticRule(
            stage="source",
            check_id=check_id,
            code=code,
            scope=source_scope,
            severity="warning",
            witness_kind="none",
            max_witnesses=0,
        )
        for check_id, code in [
            ("source_predicates", "unreachable_source"),
            ("source_overlaps", "source_overlap"),
            ("source_overlaps", "duplicate_source"),
            ("source_overlaps", "singleton_boundary_overlap"),
        ]
    ]
    diagnostics.extend(
        [
            rules.DiagnosticRule(
                stage="source",
                check_id="routing",
                code=code,
                scope=contract_scope,
                severity="error",
                witness_kind="none",
                max_witnesses=0,
            )
            for code in ("routing_gap", "routing_ambiguity")
        ]
    )
    diagnostics.append(
        rules.DiagnosticRule(
            stage="source",
            check_id="profiles",
            code="profile_counterexample",
            scope=profile_scope,
            severity="warning",
            witness_kind="pair",
            max_witnesses=0,
        )
    )
    policy = rules.ValidationPolicy(
        schema_version=1,
        policy_id="babel-native-fixture",
        required_checks=[],
        coverage_requirements=[],
        diagnostic_rules=sorted(
            diagnostics,
            key=lambda item: rules.canonical_bytes(item.model_dump(mode="json")),
        ),
    )
    rows = [
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "label": "sentinel contributor",
            "lo": 0,
            "hi": 10,
            "amount": rules.UNKNOWN_NUMERIC,
        },
        {
            "id": "00000000-0000-0000-0000-000000000002",
            "label": "zero max contributor",
            "lo": 0,
            "hi": 10,
            "amount": 0,
        },
        {
            "id": "00000000-0000-0000-0000-000000000003",
            "label": "non-winning contributor",
            "lo": 20,
            "hi": 30,
            "amount": -1,
        },
    ]
    options = dict(
        metadata=metadata,
        aggregates=aggregates,
        ruleset_id="babel-native-fixture",
        source_id_field="id",
        source_label_field="label",
        compilation_domain_ref="pricing-domain",
        domains=[domain],
        predicates=[predicate],
        languages=[],
        routing=routing,
        validation_policy=policy,
        limits=limits(),
    )
    bundle = rules.analyze_sources(rows, **options)
    expected_findings = {
        (
            "duplicate_source",
            (
                "00000000-0000-0000-0000-000000000001",
                "00000000-0000-0000-0000-000000000002",
            ),
            rules.canonical_bytes(source_scope.model_dump(mode="json")),
        ),
        (
            "source_overlap",
            (
                "00000000-0000-0000-0000-000000000001",
                "00000000-0000-0000-0000-000000000002",
            ),
            rules.canonical_bytes(source_scope.model_dump(mode="json")),
        ),
        (
            "profile_counterexample",
            (),
            rules.canonical_bytes(profile_scope.model_dump(mode="json")),
        ),
    }
    findings = tuple(bundle.validation["findings"])
    actual_findings = {
        (
            finding.code,
            tuple(sorted(finding.source_ids)),
            rules.canonical_bytes(finding.scope.model_dump(mode="json")),
        )
        for finding in findings
    }
    assert actual_findings == expected_findings
    report = bundle.validation["reports"][0]
    approvals = []
    for finding in findings:
        approval = _envelope(
            "approval",
            {
                "schema_version": 1,
                "analysis_input_id": report.analysis_input_id,
                "report_id": report.id,
                "authority_ref": "babel-fixture-review",
                "actor_ref": "babel-fixture-author",
                "decision": "approve_warnings",
                "scope": finding.scope.model_dump(mode="json"),
                "warning_ids": [finding.id],
            },
        )
        approvals.append(
            rules.WarningApproval.model_validate(
                {"id": approval["id"], **approval["payload"]}
            )
        )
    bundle = rules.attach_warning_approvals(bundle, approvals, limits=options["limits"])
    validation = rules.validate_build_input(
        rows,
        bundle=bundle,
        analysis_input_id=report.analysis_input_id,
        source_report_id=report.id,
        approvals=approvals,
        **options,
    )
    engine = rules.AccumulatorEngine(metadata, aggregates, limits=options["limits"])
    return engine, engine.build(rows, validation=validation), rows, options["limits"]
