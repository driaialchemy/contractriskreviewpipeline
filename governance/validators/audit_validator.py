from pathlib import Path
from typing import Any, Dict, List

from governance.models import DomainValidationResult, GovernanceFinding, GovernanceLevel


def validate_audit(
    repo_root: Path,
    audit_spec: Dict[str, Any],
    audit_policy: Dict[str, Any],
) -> DomainValidationResult:
    findings: List[GovernanceFinding] = []
    remediation = audit_policy.get("remediation", {})

    engine_path = repo_root / "src/orchestrator/engine.py"
    report_builder_path = repo_root / "report_builder.py"
    logs_dir = repo_root / "data/logs"

    engine_source = engine_path.read_text(encoding="utf-8")
    for section in audit_spec.get("execution_log", {}).get("required_sections", []):
        if section not in engine_source:
            findings.append(
                GovernanceFinding(
                    rule_id="execution-log-section",
                    message=f"EXECUTION_LOG exporter missing section: {section}",
                    level=GovernanceLevel.CRITICAL,
                    remediation=remediation.get("execution-log-exporter"),
                    path="src/orchestrator/engine.py",
                )
            )

    report_source = report_builder_path.read_text(encoding="utf-8")
    audit_class = audit_policy.get("audit_outputs", {}).get("session_audit_reports", {}).get(
        "class", "SessionAuditReport"
    )
    if f"class {audit_class}" not in report_source:
        findings.append(
            GovernanceFinding(
                rule_id="audit-report-builder",
                message=f"{audit_class} not found in report_builder.py",
                level=GovernanceLevel.CRITICAL,
                remediation=remediation.get("audit-report-builder"),
                path="report_builder.py",
            )
        )

    if not logs_dir.is_dir():
        findings.append(
            GovernanceFinding(
                rule_id="missing_logs_directory",
                message="data/logs directory is missing",
                level=GovernanceLevel.CRITICAL,
                remediation="Create data/logs for audit and governance evidence",
                path="data/logs",
            )
        )

    workflow_path = repo_root / audit_spec.get("ci_workflow", {}).get(
        "path", ".github/workflows/governance.yml"
    )
    if not workflow_path.is_file():
        findings.append(
            GovernanceFinding(
                rule_id="missing_workflow_file",
                message=f"CI workflow missing: {workflow_path.relative_to(repo_root).as_posix()}",
                level=GovernanceLevel.CRITICAL,
                remediation="Add GitHub Actions workflow with pytest and governance validation",
                path=workflow_path.relative_to(repo_root).as_posix(),
            )
        )
    else:
        workflow_source = workflow_path.read_text(encoding="utf-8")
        if "pytest" not in workflow_source:
            findings.append(
                GovernanceFinding(
                    rule_id="workflow_missing_pytest_step",
                    message="CI workflow must run pytest",
                    level=GovernanceLevel.CRITICAL,
                    remediation="Add pytest tests/ step to GitHub Actions workflow",
                    path=workflow_path.relative_to(repo_root).as_posix(),
                )
            )
        if "governance.validate" not in workflow_source:
            findings.append(
                GovernanceFinding(
                    rule_id="workflow_missing_governance_step",
                    message="CI workflow must run python -m governance.validate",
                    level=GovernanceLevel.CRITICAL,
                    remediation="Add governance validation step to GitHub Actions workflow",
                    path=workflow_path.relative_to(repo_root).as_posix(),
                )
            )

    passed = not any(item.level == GovernanceLevel.CRITICAL for item in findings)
    return DomainValidationResult(domain="audit", passed=passed, findings=findings)
