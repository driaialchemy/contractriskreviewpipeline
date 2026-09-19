import importlib
from pathlib import Path

import pytest

from governance.dashboard_view import (
    AUDIENCE_OPTIONS,
    GOVERNANCE_DATASET_INDEPENDENCE_NOTE,
    GovernanceCheckResult,
    empty_governance_metrics,
    extract_governance_metrics,
    load_latest_governance_report,
    resolve_governance_display_state,
    summarize_governance_for_audience,
)
from src.config import get_dataset_configuration_help, is_dataset_configured
from tests.test_dashboard_governance import _minimal_report


def test_governance_dataset_independence_note_text() -> None:
    assert "without the CUAD dataset" in GOVERNANCE_DATASET_INDEPENDENCE_NOTE
    assert "CUAD_DATASET_ZIP" in GOVERNANCE_DATASET_INDEPENDENCE_NOTE


def test_is_dataset_configured_false_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CUAD_DATASET_ZIP", raising=False)
    assert is_dataset_configured() is False
    assert "CUAD_DATASET_ZIP" in get_dataset_configuration_help()


def test_resolve_governance_display_state_prefers_session_result() -> None:
    report = _minimal_report("pass")
    session_result = GovernanceCheckResult(
        report=report,
        markdown_path="/tmp/test.md",
        json_path="/tmp/test.json",
    )
    active_report, metrics, source = resolve_governance_display_state(session_result, None)
    assert source == "session"
    assert active_report is report
    assert metrics["overall_status"] == "pass"


def test_resolve_governance_display_state_falls_back_to_disk_report(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    report = _minimal_report("pass_with_warnings")
    md_path = logs_dir / "governance_report_20260101_120000.md"
    json_path = logs_dir / "governance_report_20260101_120000.json"
    md_path.write_text("# report", encoding="utf-8")
    json_path.write_text(report.model_dump_json(), encoding="utf-8")
    latest = load_latest_governance_report(logs_dir)

    active_report, metrics, source = resolve_governance_display_state(None, latest)
    assert source == "disk"
    assert active_report is not None
    assert metrics["overall_status"] == "pass_with_warnings"


def test_resolve_governance_display_state_empty_when_no_reports() -> None:
    active_report, metrics, source = resolve_governance_display_state(None, None)
    assert source == "none"
    assert active_report is None
    assert metrics == empty_governance_metrics()


def test_audience_summaries_are_materially_different() -> None:
    report = _minimal_report("pass_with_warnings")
    metrics = extract_governance_metrics(report)
    summaries = {
        audience: summarize_governance_for_audience(report, metrics, audience)
        for audience in AUDIENCE_OPTIONS
    }
    assert summaries["Executive"] != summaries["Technical"]
    assert summaries["Technical"] != summaries["User"]
    assert "Recommended decision" in summaries["Executive"]
    assert "Validator domains" in summaries["Technical"]
    assert "checked itself" in summaries["User"].lower()


def test_dashboard_import_without_dataset_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CUAD_DATASET_ZIP", raising=False)
    module = importlib.import_module("dashboard")
    assert module.is_dataset_configured() is False
