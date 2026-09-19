import asyncio
from pathlib import Path

import pytest

from governance.dashboard_view import (
    AUDIENCE_OPTIONS,
    empty_governance_metrics,
    extract_governance_metrics,
    format_governance_summary_for_audience,
    get_executive_decision,
    get_status_display_label,
    load_latest_governance_report,
    metrics_from_report_files,
    summarize_governance_for_audience,
)
from governance.models import DomainValidationResult, GovernanceFinding, GovernanceLevel, GovernanceReport


PROJECT_ROOT = Path(__file__).resolve().parent.parent

def _minimal_report(overall_status: str = "pass") -> GovernanceReport:
    empty_domain = DomainValidationResult(domain="repo", passed=True, findings=[])
    report = GovernanceReport(
        repo_validation=empty_domain,
        spec_validation=DomainValidationResult(domain="spec", passed=True, findings=[]),
        policy_validation=DomainValidationResult(domain="policy", passed=True, findings=[]),
        agent_validation=DomainValidationResult(domain="agent", passed=True, findings=[]),
        pipeline_validation=DomainValidationResult(domain="pipeline", passed=True, findings=[]),
        audit_validation=DomainValidationResult(domain="audit", passed=True, findings=[]),
        known_limitations=GovernanceReport.default_known_limitations(),
    )
    if overall_status == "fail":
        report.repo_validation = DomainValidationResult(
            domain="repo",
            passed=False,
            findings=[
                GovernanceFinding(
                    rule_id="missing_required_file",
                    message="Required file missing: example.py",
                    level=GovernanceLevel.CRITICAL,
                    remediation="Restore the file",
                    path="example.py",
                )
            ],
        )
    elif overall_status == "pass_with_warnings":
        report.repo_validation = DomainValidationResult(
            domain="repo",
            passed=True,
            findings=[
                GovernanceFinding(
                    rule_id="agent-documented",
                    message="Missing docstring",
                    level=GovernanceLevel.WARNING,
                    remediation="Add docstring",
                )
            ],
        )
    report.compute_overall_status()
    return report


def test_extract_governance_metrics_pass() -> None:
    report = _minimal_report("pass")
    metrics = extract_governance_metrics(report)
    assert metrics["overall_status"] == "pass"
    assert metrics["critical_count"] == 0
    assert metrics["exit_code"] == 0


def test_extract_governance_metrics_fail() -> None:
    report = _minimal_report("fail")
    metrics = extract_governance_metrics(report)
    assert metrics["overall_status"] == "fail"
    assert metrics["critical_count"] == 1
    assert metrics["exit_code"] == 1


def test_extract_governance_metrics_pass_with_warnings() -> None:
    report = _minimal_report("pass_with_warnings")
    metrics = extract_governance_metrics(report)
    assert metrics["overall_status"] == "pass_with_warnings"
    assert metrics["warning_count"] == 1
    assert metrics["exit_code"] == 0


def test_empty_governance_metrics_when_no_reports(tmp_path: Path) -> None:
    metrics = empty_governance_metrics()
    assert metrics["overall_status"] == "unknown"
    assert load_latest_governance_report(tmp_path / "logs") is None


def test_load_latest_governance_report_when_no_reports(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    assert load_latest_governance_report(logs_dir) is None


def test_load_latest_governance_report_reads_files(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    md_path = logs_dir / "governance_report_20260101_120000.md"
    json_path = logs_dir / "governance_report_20260101_120000.json"
    md_path.write_text("# Report", encoding="utf-8")
    report = _minimal_report("pass")
    json_path.write_text(report.model_dump_json(), encoding="utf-8")

    latest = load_latest_governance_report(logs_dir)
    assert latest is not None
    assert latest.markdown_content == "# Report"
    metrics = metrics_from_report_files(latest)
    assert metrics["overall_status"] == "pass"


@pytest.mark.parametrize("audience", AUDIENCE_OPTIONS)
def test_audience_specific_summary_generation(audience: str) -> None:
    report = _minimal_report("pass_with_warnings")
    metrics = extract_governance_metrics(report)
    summary = summarize_governance_for_audience(report, metrics, audience)  # type: ignore[arg-type]
    assert summary
    assert "warning" in summary.lower() or "Warning" in summary


def test_executive_summary_mentions_decision() -> None:
    report = _minimal_report("fail")
    metrics = extract_governance_metrics(report)
    summary = format_governance_summary_for_audience(report, metrics, "Executive")
    assert "Stop and remediate" in summary or "remediate" in summary.lower()


def test_user_summary_plain_language() -> None:
    report = _minimal_report("pass")
    metrics = extract_governance_metrics(report)
    summary = format_governance_summary_for_audience(report, metrics, "User")
    assert "checked itself" in summary.lower()


def test_technical_summary_includes_domains() -> None:
    report = _minimal_report("pass")
    metrics = extract_governance_metrics(report)
    summary = format_governance_summary_for_audience(report, metrics, "Technical")
    assert "repo" in summary
    assert "validation_only" in summary or "CI" in summary


def test_status_display_labels() -> None:
    assert get_status_display_label("pass") == "Passed"
    assert get_status_display_label("pass_with_warnings") == "Passed with warnings"
    assert get_status_display_label("fail") == "Failed"


def test_executive_decision_for_fail_status() -> None:
    metrics = extract_governance_metrics(_minimal_report("fail"))
    assert "remediate" in get_executive_decision(metrics).lower()
