import ast
from pathlib import Path
from typing import Any, Dict, List

from governance.models import DomainValidationResult, GovernanceFinding, GovernanceLevel


def validate_pipeline(
    repo_root: Path,
    pipeline_spec: Dict[str, Any],
    audit_policy: Dict[str, Any],
) -> DomainValidationResult:
    findings: List[GovernanceFinding] = []
    remediation = audit_policy.get("remediation", {})

    state_path = repo_root / "src/orchestrator/state.py"
    risk_path = repo_root / "src/agents/risk.py"
    summary_path = repo_root / "src/agents/summary.py"
    engine_path = repo_root / "src/orchestrator/engine.py"

    required_risk_fields = pipeline_spec.get("risk_output", {}).get("required_fields", [])
    risk_model_fields = _extract_model_fields(state_path, "RiskFlag")
    for field_name in required_risk_fields:
        if field_name not in risk_model_fields:
            rule_id = "risk-severity-present" if field_name == "severity" else "risk-reason-present"
            if field_name == "human_review_status":
                rule_id = "human-review-on-high-critical"
            findings.append(
                GovernanceFinding(
                    rule_id=rule_id,
                    message=f"RiskFlag missing required field: {field_name}",
                    level=GovernanceLevel.CRITICAL,
                    remediation=remediation.get(rule_id),
                    path="src/orchestrator/state.py",
                )
            )

    risk_source = risk_path.read_text(encoding="utf-8")
    if "human_review_status" not in risk_source:
        findings.append(
            GovernanceFinding(
                rule_id="human-review-on-high-critical",
                message="RiskAgent does not set human_review_status on findings",
                level=GovernanceLevel.CRITICAL,
                remediation=remediation.get("human-review-on-high-critical"),
                path="src/agents/risk.py",
            )
        )
    elif '"required"' not in risk_source and "'required'" not in risk_source:
        findings.append(
            GovernanceFinding(
                rule_id="human-review-on-high-critical",
                message="RiskAgent must mark high/critical findings with human_review_status='required'",
                level=GovernanceLevel.CRITICAL,
                remediation=remediation.get("human-review-on-high-critical"),
                path="src/agents/risk.py",
            )
        )

    summary_source = summary_path.read_text(encoding="utf-8")
    traceability_checks = [
        ("risk_flags", "summary-traceability"),
        ("clause_by_clause", "summary-traceability"),
        ("flag_by_clause", "summary-traceability"),
    ]
    for token, rule_id in traceability_checks:
        if token not in summary_source:
            findings.append(
                GovernanceFinding(
                    rule_id=rule_id,
                    message=f"SummaryAgent missing traceability marker: {token}",
                    level=GovernanceLevel.CRITICAL,
                    remediation=remediation.get("summary-traceability"),
                    path="src/agents/summary.py",
                )
            )

    engine_source = engine_path.read_text(encoding="utf-8")
    if "export_execution_log" not in engine_source or "EXECUTION_LOG.md" not in engine_source:
        findings.append(
            GovernanceFinding(
                rule_id="execution-log-exporter",
                message="Orchestrator must export EXECUTION_LOG.md",
                level=GovernanceLevel.CRITICAL,
                remediation=remediation.get("execution-log-exporter"),
                path="src/orchestrator/engine.py",
            )
        )

    expected_stages = [stage["name"] for stage in pipeline_spec.get("stages", [])]
    for stage in expected_stages:
        if stage == "complete":
            continue
        if stage not in engine_source and stage not in risk_source + summary_source:
            findings.append(
                GovernanceFinding(
                    rule_id="missing_pipeline_stage",
                    message=f"Pipeline stage not referenced in source: {stage}",
                    level=GovernanceLevel.WARNING,
                    remediation="Ensure orchestrator and agents implement all pipeline stages",
                    path="src/orchestrator/engine.py",
                )
            )

    passed = not any(item.level == GovernanceLevel.CRITICAL for item in findings)
    return DomainValidationResult(domain="pipeline", passed=passed, findings=findings)


def _extract_model_fields(path: Path, model_name: str) -> List[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    fields: List[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == model_name:
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    fields.append(item.target.id)
                elif isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            fields.append(target.id)
    return fields
