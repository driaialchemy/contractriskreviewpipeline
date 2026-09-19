import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from governance.models import GovernanceReport
from governance.reports.governance_report import write_governance_reports
from governance.validate import run_governance_validation
from governance.validators.spec_loader import resolve_repo_root

Audience = Literal["Executive", "Technical", "User"]
AUDIENCE_OPTIONS: Tuple[Audience, ...] = ("Executive", "Technical", "User")


@dataclass
class GovernanceCheckResult:
    report: GovernanceReport
    markdown_path: str
    json_path: str


@dataclass
class LatestGovernanceReportFiles:
    markdown_path: Path
    json_path: Optional[Path]
    markdown_content: str
    json_content: Optional[Dict[str, Any]]
    modified_at: datetime


def extract_governance_metrics(report: GovernanceReport) -> Dict[str, Any]:
    counts = report.severity_counts
    return {
        "overall_status": report.overall_status,
        "risk_level": report.risk_level,
        "exit_code": report.exit_code,
        "critical_count": counts["critical"],
        "warning_count": counts["warning"],
        "info_count": counts["info"],
        "timestamp": report.timestamp.isoformat(),
        "evidence_paths": list(report.evidence_paths),
        "passed": report.overall_status in {"pass", "pass_with_warnings"},
        "failed": report.overall_status == "fail",
    }


def empty_governance_metrics() -> Dict[str, Any]:
    return {
        "overall_status": "unknown",
        "risk_level": "unknown",
        "exit_code": 0,
        "critical_count": 0,
        "warning_count": 0,
        "info_count": 0,
        "timestamp": None,
        "evidence_paths": [],
        "passed": False,
        "failed": False,
    }


def list_governance_report_markdown_files(logs_dir: Path, limit: int = 10) -> List[Path]:
    if not logs_dir.is_dir():
        return []
    files = sorted(
        logs_dir.glob("governance_report_*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return files[:limit]


def _json_path_for_markdown(md_path: Path) -> Path:
    stamp = md_path.stem.replace("governance_report_", "", 1)
    return md_path.parent / f"governance_report_{stamp}.json"


def json_path_for_markdown_report(md_path: Path) -> Path:
    return _json_path_for_markdown(md_path)


def load_latest_governance_report(logs_dir: Path) -> Optional[LatestGovernanceReportFiles]:
    markdown_files = list_governance_report_markdown_files(logs_dir, limit=1)
    if not markdown_files:
        return None

    md_path = markdown_files[0]
    json_path = _json_path_for_markdown(md_path)
    markdown_content = md_path.read_text(encoding="utf-8")
    json_content: Optional[Dict[str, Any]] = None
    if json_path.is_file():
        json_content = json.loads(json_path.read_text(encoding="utf-8"))

    modified_at = datetime.fromtimestamp(md_path.stat().st_mtime)
    return LatestGovernanceReportFiles(
        markdown_path=md_path,
        json_path=json_path if json_path.is_file() else None,
        markdown_content=markdown_content,
        json_content=json_content,
        modified_at=modified_at,
    )


def governance_report_from_json(data: Dict[str, Any]) -> GovernanceReport:
    return GovernanceReport.model_validate(data)


def metrics_from_report_files(latest: LatestGovernanceReportFiles) -> Dict[str, Any]:
    if latest.json_content is None:
        return empty_governance_metrics()
    report = governance_report_from_json(latest.json_content)
    report.compute_overall_status()
    return extract_governance_metrics(report)


def metrics_from_check_result(result: GovernanceCheckResult) -> Dict[str, Any]:
    return extract_governance_metrics(result.report)


async def run_governance_check(repo_root: Path | None = None) -> GovernanceCheckResult:
    root = repo_root or resolve_repo_root()
    report = await run_governance_validation(root)
    md_path, json_path = await write_governance_reports(report, root)
    report.evidence_paths = [md_path, json_path]
    return GovernanceCheckResult(report=report, markdown_path=md_path, json_path=json_path)


def run_governance_check_sync(repo_root: Path | None = None) -> GovernanceCheckResult:
    return asyncio.run(run_governance_check(repo_root))


def get_architecture_explanation(audience: Audience) -> str:
    if audience == "Executive":
        return (
            "This contract-review system is governed by a specification-driven (SDD) layer. "
            "Machine-readable rules define how the pipeline should behave. Policy-as-code checks "
            "whether the repository matches those rules. CI/CD runs those checks automatically. "
            "Audit reports provide evidence that checks ran and what they found."
        )
    if audience == "Technical":
        return (
            "**SDD methodology:** Specs in `governance/specs/` define expected agents, pipeline "
            "stages, risk fields, audit artifacts, and CI expectations.\n\n"
            "**Policy-as-code:** YAML policies in `governance/policies/` are validated by Python "
            "validators with Pydantic schema checks.\n\n"
            "**CI/CD execution:** GitHub Actions runs `pytest` and `python -m governance.validate`; "
            "critical findings fail the job.\n\n"
            "**Audit evidence:** Reports under `data/logs/governance_report_*` plus pipeline "
            "execution logs and session audit reports."
        )
    return (
        "The governance layer is like a checklist for the whole project. It reads the project's "
        "rules (specs) and checks whether the code and reports follow them (policies). "
        "Automated tests in CI run the same checks. When checks finish, they save a report you "
        "can review as proof of what was checked."
    )


def get_status_display_label(overall_status: str) -> str:
    mapping = {
        "pass": "Passed",
        "pass_with_warnings": "Passed with warnings",
        "fail": "Failed",
        "unknown": "No report yet",
    }
    return mapping.get(overall_status, overall_status.replace("_", " ").title())


def get_executive_decision(metrics: Dict[str, Any]) -> str:
    if metrics["overall_status"] == "fail" or metrics["critical_count"] > 0:
        return "Stop and remediate critical governance issues before relying on this environment for production use."
    if metrics["overall_status"] == "pass_with_warnings" or metrics["warning_count"] > 0:
        return "Proceed with caution — review warnings and confirm they are acceptable."
    if metrics["overall_status"] == "pass":
        return "Proceed — governance checks passed; continue using the system with normal review habits."
    return "Run a governance check to assess whether the system is governed and auditable."


def summarize_governance_for_audience(
    report: Optional[GovernanceReport],
    metrics: Dict[str, Any],
    audience: Audience,
) -> str:
    return format_governance_summary_for_audience(report, metrics, audience)


def format_governance_summary_for_audience(
    report: Optional[GovernanceReport],
    metrics: Dict[str, Any],
    audience: Audience,
) -> str:
    status_label = get_status_display_label(str(metrics.get("overall_status", "unknown")))

    if audience == "Executive":
        lines = [
            f"**Governance status:** {status_label}",
            f"**Critical issues:** {metrics.get('critical_count', 0)}",
            f"**Warnings:** {metrics.get('warning_count', 0)}",
            "",
            "The system is designed to be governed (rules defined), auditable (reports saved), "
            "and checkable in CI. Critical governance failures mean structural or compliance gaps "
            "that should be fixed before high-stakes use.",
            "",
            f"**Recommended decision:** {get_executive_decision(metrics)}",
        ]
        return "\n".join(lines)

    if audience == "Technical":
        lines = [
            f"Overall status: `{metrics.get('overall_status', 'unknown')}` "
            f"(exit code {metrics.get('exit_code', 0)})",
            f"Severity counts — critical: {metrics.get('critical_count', 0)}, "
            f"warning: {metrics.get('warning_count', 0)}, info: {metrics.get('info_count', 0)}",
        ]
        if metrics.get("timestamp"):
            lines.append(f"Report timestamp: {metrics['timestamp']}")
        if metrics.get("evidence_paths"):
            lines.append("Evidence paths:")
            for path in metrics["evidence_paths"]:
                lines.append(f"- `{path}`")

        if report is not None:
            lines.extend(["", "Validator domains:"])
            for domain in [
                report.repo_validation,
                report.spec_validation,
                report.policy_validation,
                report.agent_validation,
                report.pipeline_validation,
                report.audit_validation,
            ]:
                status = "PASS" if domain.passed else "FAIL"
                lines.append(
                    f"- {domain.domain}: {status} "
                    f"(critical={domain.critical_count}, warning={domain.warning_count}, "
                    f"info={domain.info_count})"
                )
            if report.failures:
                lines.extend(["", "Critical findings:"])
                for finding in report.failures[:10]:
                    lines.append(f"- [{finding.rule_id}] {finding.message}")
            if report.known_limitations:
                lines.extend(["", "Known limitations:"])
                for item in report.known_limitations[:4]:
                    lines.append(f"- {item}")
        lines.append("")
        lines.append(
            "CI runs `python -m governance.validate`; critical findings fail the workflow. "
            "Default enforcement mode is validation_only (does not block contract pipeline runtime)."
        )
        return "\n".join(lines)

    lines = [
        f"The system checked itself against its rules: **{status_label}**.",
        "",
        "- **Pass** means no serious problems were found.",
        "- **Warnings** mean something should be reviewed, but the system can still run.",
        "- **Failures** mean something important needs to be fixed.",
        "",
        f"Right now there are {metrics.get('critical_count', 0)} critical item(s), "
        f"{metrics.get('warning_count', 0)} warning(s), and {metrics.get('info_count', 0)} info note(s).",
    ]
    if metrics.get("overall_status") == "fail":
        lines.append("**What to do next:** Fix critical issues, then run the governance check again.")
    elif metrics.get("overall_status") == "pass_with_warnings":
        lines.append("**What to do next:** Review warnings when you have time; the system can still be used.")
    elif metrics.get("overall_status") == "pass":
        lines.append("**What to do next:** No urgent action — keep using the system normally.")
    else:
        lines.append("**What to do next:** Click **Run Governance Check** to run the first check.")
    return "\n".join(lines)


def get_what_governance_checks(audience: Audience) -> str:
    if audience == "Executive":
        return (
            "Checks whether required project structure, agents, pipeline contracts, audit outputs, "
            "and CI configuration match defined governance rules — supporting confidence, compliance, "
            "and audit readiness."
        )
    if audience == "Technical":
        return (
            "Validates required files/folders, schema-valid specs/policies, agent structure, "
            "RiskFlag/summary traceability, audit log exporters, CI workflow steps, and sensitive "
            "path categories (critical vs generated/cache)."
        )
    return (
        "Checks that the project has the right files, that the three review agents are set up correctly, "
        "that risk reports include required details, and that check results are saved as reports."
    )


def get_remediation_lines(report: Optional[GovernanceReport]) -> List[str]:
    if report is None:
        return ["Run a governance check to generate remediation guidance."]
    lines: List[str] = []
    seen: set[str] = set()
    for finding in report.all_findings:
        if not finding.remediation or finding.level.value == "info":
            continue
        key = f"{finding.rule_id}:{finding.remediation}"
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"{finding.rule_id}: {finding.remediation}")
    return lines or ["No remediation required for critical or warning findings."]


GOVERNANCE_DATASET_INDEPENDENCE_NOTE = (
    "The Governance Layer can be reviewed without the CUAD dataset. "
    "Contract Review requires CUAD_DATASET_ZIP because it needs access to the "
    "local CUAD dataset zip file."
)


def resolve_governance_display_state(
    check_result: Optional[GovernanceCheckResult],
    latest_files: Optional[LatestGovernanceReportFiles],
) -> tuple[Optional[GovernanceReport], Dict[str, Any], str]:
    """Prefer in-session check result; fall back to latest on-disk JSON report."""
    if check_result is not None:
        return (
            check_result.report,
            metrics_from_check_result(check_result),
            "session",
        )
    if latest_files is not None and latest_files.json_content is not None:
        report = governance_report_from_json(latest_files.json_content)
        report.compute_overall_status()
        return report, metrics_from_report_files(latest_files), "disk"
    return None, empty_governance_metrics(), "none"
