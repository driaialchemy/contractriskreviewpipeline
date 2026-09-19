import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

from governance.models import DomainValidationResult, GovernanceFinding, GovernanceReport


def _format_findings(findings: List[GovernanceFinding], heading: str) -> List[str]:
    lines = [f"## {heading}", ""]
    if not findings:
        lines.append("- None")
        lines.append("")
        return lines
    for finding in findings:
        path_suffix = f" (`{finding.path}`)" if finding.path else ""
        enforcement = finding.enforcement_mode.value
        lines.append(
            f"- **[{finding.level.value}] {finding.rule_id}** "
            f"({enforcement}){path_suffix}: {finding.message}"
        )
        if finding.remediation:
            lines.append(f"  - Remediation: {finding.remediation}")
    lines.append("")
    return lines


def _domain_status_lines(domain: DomainValidationResult) -> List[str]:
    status = "PASS" if domain.passed else "FAIL"
    return [
        f"- **{domain.domain}**: {status} "
        f"(critical={domain.critical_count}, warnings={domain.warning_count}, info={domain.info_count})"
    ]


def render_markdown_report(report: GovernanceReport) -> str:
    generated_at = report.timestamp.isoformat()
    counts = report.severity_counts
    domains = [
        report.repo_validation,
        report.spec_validation,
        report.policy_validation,
        report.agent_validation,
        report.pipeline_validation,
        report.audit_validation,
    ]

    lines: List[str] = [
        "# CUAD SDD Governance Report",
        "",
        f"**Generated:** {generated_at}",
        f"**Overall Status:** {report.overall_status}",
        f"**Risk Level:** {report.risk_level}",
        f"**Exit Code:** {report.exit_code}",
        f"**Exit Behavior:** {report.exit_behavior}",
        f"**Default Enforcement Mode:** {report.default_enforcement_mode}",
        "",
        "## Severity Counts",
        "",
        f"- Critical: {counts['critical']}",
        f"- Warning: {counts['warning']}",
        f"- Info: {counts['info']}",
        "",
        "## Validation vs Enforcement",
        "",
        "- **validation_only:** Reports conformance against specs/policies; default for all rules in this phase.",
        "- **enforcement_ready:** Reserved for future hooks that could block merges or deployments.",
        "- **execution_blocking:** Not used at runtime today; the CUAD pipeline is not stopped except via CI/CLI exit on critical governance failures.",
        "- Contract **human_review_status** is recorded on high/critical findings but does not prevent summary generation.",
        "",
        "## Validation Summary",
        "",
    ]
    for domain in domains:
        lines.extend(_domain_status_lines(domain))
    lines.extend(
        [
            "",
            "## Domain Details",
            "",
            f"- Repo validation status: {'PASS' if report.repo_validation.passed else 'FAIL'}",
            f"- Spec validation status: {'PASS' if report.spec_validation.passed else 'FAIL'}",
            f"- Policy validation status: {'PASS' if report.policy_validation.passed else 'FAIL'}",
            f"- Agent validation status: {'PASS' if report.agent_validation.passed else 'FAIL'}",
            f"- Pipeline validation status: {'PASS' if report.pipeline_validation.passed else 'FAIL'}",
            f"- Audit validation status: {'PASS' if report.audit_validation.passed else 'FAIL'}",
            "",
        ]
    )
    lines.extend(_format_findings(report.failures, "Critical Findings"))
    lines.extend(_format_findings(report.warnings, "Warning Findings"))
    lines.extend(_format_findings(report.infos, "Info Findings"))

    remediation_findings = [
        item for item in report.all_findings if item.remediation and item.level.value != "info"
    ]
    lines.extend(["## Recommended Remediation", ""])
    if remediation_findings:
        seen: set[str] = set()
        for finding in remediation_findings:
            key = f"{finding.rule_id}:{finding.remediation}"
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"- **{finding.rule_id}**: {finding.remediation}")
    else:
        lines.append("- No remediation required for critical or warning findings.")
    lines.append("")

    lines.extend(["## Evidence File Paths", ""])
    if report.evidence_paths:
        for path in report.evidence_paths:
            lines.append(f"- `{path}`")
    else:
        lines.append("- Evidence paths recorded after report write.")
    lines.append("")

    lines.extend(["## Known Limitations", ""])
    for limitation in report.known_limitations:
        lines.append(f"- {limitation}")
    lines.append("")

    lines.extend(
        [
            "## SDD Layers",
            "",
            "- **Methodology (SDD):** Machine-readable specs under `governance/specs/`",
            "- **Policy-as-code:** YAML policies enforced by Python validators with Pydantic schema checks",
            "- **CI/CD execution:** GitHub Actions runs pytest and governance validation",
            "- **Audit evidence:** This report and pipeline audit logs under `data/logs/`",
            "",
        ]
    )
    return "\n".join(lines)


def _report_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


async def write_governance_reports(
    report: GovernanceReport,
    repo_root: Path,
) -> Tuple[str, str]:
    logs_dir = repo_root / "data" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    stamp = _report_timestamp()
    md_path = logs_dir / f"governance_report_{stamp}.md"
    json_path = logs_dir / f"governance_report_{stamp}.json"

    markdown = render_markdown_report(report)

    def _write_files() -> None:
        md_path.write_text(markdown, encoding="utf-8")
        json_path.write_text(
            json.dumps(report.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

    await asyncio.to_thread(_write_files)
    return str(md_path.resolve()), str(json_path.resolve())
