import asyncio
from pathlib import Path

from governance.models import GovernanceLevel
from governance.reports.governance_report import render_markdown_report, write_governance_reports
from governance.schemas import validate_policy_document, validate_spec_document
from governance.validate import run_governance_validation
from governance.validators.agent_validator import validate_agents
from governance.validators.repo_validator import validate_repo
from governance.validators.spec_loader import load_policies, load_specs


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_specs_load_successfully() -> None:
    specs = asyncio.run(load_specs())
    assert "agent-governance.spec.yaml" in specs
    assert specs["agent-governance.spec.yaml"]["agents"]


def test_policies_load_successfully() -> None:
    policies = asyncio.run(load_policies())
    assert "repo_policy.yaml" in policies
    assert policies["repo_policy.yaml"]["critical_sensitive_paths"]


def test_schema_validation_for_valid_specs() -> None:
    specs = asyncio.run(load_specs())
    for filename, document in specs.items():
        model, findings = validate_spec_document(filename, document)
        assert model is not None
        assert not findings


def test_schema_validation_for_valid_policies() -> None:
    policies = asyncio.run(load_policies())
    for filename, document in policies.items():
        model, findings = validate_policy_document(filename, document)
        assert model is not None
        assert not findings


def test_schema_validation_for_invalid_spec(tmp_path: Path) -> None:
    invalid = {"version": "1.0", "description": "broken", "unexpected_field": True}
    _, findings = validate_spec_document("agent-governance.spec.yaml", invalid)
    assert findings
    assert any(item.rule_id == "schema_validation_error" for item in findings)
    assert all(item.level == GovernanceLevel.CRITICAL for item in findings)


def test_schema_validation_for_invalid_policy(tmp_path: Path) -> None:
    invalid = {"version": "1.0"}
    _, findings = validate_policy_document("repo_policy.yaml", invalid)
    assert findings
    assert any(item.rule_id == "schema_validation_error" for item in findings)


def test_required_files_validation_works() -> None:
    policies = asyncio.run(load_policies())
    result = validate_repo(PROJECT_ROOT, policies["repo_policy.yaml"])
    assert result.passed
    assert not any(item.level == GovernanceLevel.CRITICAL for item in result.findings)


def test_generated_cache_paths_are_info_not_critical() -> None:
    policies = asyncio.run(load_policies())
    result = validate_repo(PROJECT_ROOT, policies["repo_policy.yaml"])
    cache_findings = [
        item for item in result.findings if item.rule_id == "generated_cache_path_present"
    ]
    assert cache_findings
    assert all(item.level == GovernanceLevel.INFO for item in cache_findings)


def test_critical_sensitive_paths_use_critical_level(tmp_path: Path) -> None:
    policies = asyncio.run(load_policies())
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "tests").mkdir()
    (repo_root / "tests" / "test_placeholder.py").write_text("def test_x(): pass\n", encoding="utf-8")
    (repo_root / ".env").write_text("SECRET=1\n", encoding="utf-8")

    policy = dict(policies["repo_policy.yaml"])
    policy["required_files"] = []
    policy["required_directories"] = ["tests"]

    result = validate_repo(repo_root, policy)
    critical_findings = [
        item for item in result.findings if item.rule_id == "critical_sensitive_path_present"
    ]
    assert critical_findings
    assert all(item.level == GovernanceLevel.CRITICAL for item in critical_findings)


def test_agent_validation_works() -> None:
    specs = asyncio.run(load_specs())
    policies = asyncio.run(load_policies())
    result = validate_agents(
        PROJECT_ROOT,
        specs["agent-governance.spec.yaml"],
        policies["agent_policy.yaml"],
    )
    assert result.passed


def test_governance_exit_code_logic() -> None:
    report = asyncio.run(run_governance_validation(PROJECT_ROOT))
    report.compute_overall_status()
    if report.failures:
        assert report.exit_code == 1
    else:
        assert report.exit_code == 0


def test_audit_report_generation_works() -> None:
    report = asyncio.run(run_governance_validation(PROJECT_ROOT))
    md_path, json_path = asyncio.run(write_governance_reports(report, PROJECT_ROOT))
    report.evidence_paths = [md_path, json_path]

    markdown = render_markdown_report(report)
    assert "Severity Counts" in markdown
    assert "Known Limitations" in markdown
    assert "Validation vs Enforcement" in markdown
    assert Path(md_path).is_file()
    assert Path(json_path).is_file()


def test_full_governance_validation_passes_for_current_repo() -> None:
    report = asyncio.run(run_governance_validation(PROJECT_ROOT))
    report.compute_overall_status()
    assert not report.failures
    assert report.overall_status in {"pass", "pass_with_warnings"}
    assert report.exit_code == 0


def test_full_governance_validation_fails_when_required_file_missing(
    tmp_path: Path,
) -> None:
    missing_root = tmp_path / "repo"
    missing_root.mkdir()
    (missing_root / "main.py").write_text("# placeholder\n", encoding="utf-8")

    policies = asyncio.run(load_policies())
    result = validate_repo(missing_root, policies["repo_policy.yaml"])
    assert not result.passed
    assert any(item.rule_id == "missing_required_file" for item in result.findings)
    assert any(item.level == GovernanceLevel.CRITICAL for item in result.findings)
