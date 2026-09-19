import asyncio
from pathlib import Path

from governance.models import GovernanceReport
from governance.validators.agent_validator import validate_agents
from governance.validators.audit_validator import validate_audit
from governance.validators.pipeline_validator import validate_pipeline
from governance.validators.repo_validator import validate_repo
from governance.validators.spec_loader import (
    load_policies,
    load_specs,
    resolve_repo_root,
    validate_policy_schemas,
    validate_spec_schemas,
)


async def run_governance_validation(repo_root: Path | None = None) -> GovernanceReport:
    root = repo_root or resolve_repo_root()
    specs = await load_specs()
    policies = await load_policies()

    repo_result = validate_repo(root, policies["repo_policy.yaml"])
    spec_result = validate_spec_schemas(specs)
    policy_result = validate_policy_schemas(policies)
    agent_result = validate_agents(
        root,
        specs["agent-governance.spec.yaml"],
        policies["agent_policy.yaml"],
    )
    pipeline_result = validate_pipeline(
        root,
        specs["pipeline-governance.spec.yaml"],
        policies["audit_policy.yaml"],
    )
    audit_result = validate_audit(
        root,
        specs["audit-governance.spec.yaml"],
        policies["audit_policy.yaml"],
    )

    report = GovernanceReport(
        repo_validation=repo_result,
        spec_validation=spec_result,
        policy_validation=policy_result,
        agent_validation=agent_result,
        pipeline_validation=pipeline_result,
        audit_validation=audit_result,
        known_limitations=GovernanceReport.default_known_limitations(),
    )
    report.compute_overall_status()
    return report


def print_console_summary(report: GovernanceReport) -> None:
    counts = report.severity_counts
    print("=" * 72)
    print("CUAD SDD GOVERNANCE VALIDATION")
    print("=" * 72)
    print(f"Timestamp:       {report.timestamp.isoformat()}")
    print(f"Overall Status:  {report.overall_status.upper()}")
    print(f"Risk Level:      {report.risk_level.upper()}")
    print(f"Exit Code:       {report.exit_code} ({report.exit_behavior})")
    print(f"Enforcement:     {report.default_enforcement_mode} (validation reports only; no runtime pipeline block)")
    print(
        f"Severity Counts: critical={counts['critical']} "
        f"warning={counts['warning']} info={counts['info']}"
    )
    print("-" * 72)
    domains = [
        report.repo_validation,
        report.spec_validation,
        report.policy_validation,
        report.agent_validation,
        report.pipeline_validation,
        report.audit_validation,
    ]
    for domain in domains:
        status = "PASS" if domain.passed else "FAIL"
        print(
            f"{domain.domain:10} {status:4}  "
            f"critical={domain.critical_count} "
            f"warnings={domain.warning_count} info={domain.info_count}"
        )
    print("-" * 72)
    if report.failures:
        print("CRITICAL FINDINGS:")
        for finding in report.failures:
            location = f" ({finding.path})" if finding.path else ""
            print(f"  - [{finding.rule_id}] {finding.message}{location}")
    if report.warnings:
        print("WARNINGS:")
        for finding in report.warnings:
            location = f" ({finding.path})" if finding.path else ""
            print(f"  - [{finding.rule_id}] {finding.message}{location}")
    if report.infos:
        print("INFO:")
        for finding in report.infos:
            location = f" ({finding.path})" if finding.path else ""
            print(f"  - [{finding.rule_id}] {finding.message}{location}")
    if not report.failures and not report.warnings and not report.infos:
        print("No governance findings. Repository conforms to SDD policies.")
    print("=" * 72)


async def main_async() -> int:
    from governance.reports.governance_report import write_governance_reports

    root = resolve_repo_root()
    report = await run_governance_validation(root)
    md_path, json_path = await write_governance_reports(report, root)
    report.evidence_paths = [md_path, json_path]

    print_console_summary(report)
    print(f"Governance report (Markdown): {md_path}")
    print(f"Governance report (JSON):     {json_path}")

    return report.exit_code


def main() -> None:
    exit_code = asyncio.run(main_async())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
