from pathlib import Path
from typing import Any, Dict, List

from governance.models import DomainValidationResult, GovernanceFinding, GovernanceLevel
from governance.validators.spec_loader import list_matching_paths


def _level_from_name(level_name: str) -> GovernanceLevel:
    normalized = level_name.lower()
    if normalized == "critical":
        return GovernanceLevel.CRITICAL
    if normalized == "warning":
        return GovernanceLevel.WARNING
    return GovernanceLevel.INFO


def validate_repo(repo_root: Path, repo_policy: Dict[str, Any]) -> DomainValidationResult:
    findings: List[GovernanceFinding] = []
    remediation_map = {
        "missing_required_file": "Restore the missing file listed in repo_policy.yaml",
        "missing_required_directory": "Create the missing directory listed in repo_policy.yaml",
        "missing_tests": "Add pytest tests under the tests/ directory",
        "critical_sensitive_path_present": "Remove or protect critical sensitive files; never commit secrets or production data",
        "generated_cache_path_present": "Safe to ignore locally; add to .gitignore; not equivalent to secrets",
    }

    for rel_path in repo_policy.get("required_files", []):
        target = repo_root / rel_path
        if not target.is_file():
            findings.append(
                GovernanceFinding(
                    rule_id="missing_required_file",
                    message=f"Required file missing: {rel_path}",
                    level=GovernanceLevel.CRITICAL,
                    remediation=remediation_map["missing_required_file"],
                    path=rel_path,
                )
            )

    for rel_dir in repo_policy.get("required_directories", []):
        target = repo_root / rel_dir
        if not target.is_dir():
            findings.append(
                GovernanceFinding(
                    rule_id="missing_required_directory",
                    message=f"Required directory missing: {rel_dir}",
                    level=GovernanceLevel.CRITICAL,
                    remediation=remediation_map["missing_required_directory"],
                    path=rel_dir,
                )
            )

    tests_dir = repo_root / repo_policy.get("tests", {}).get("directory", "tests")
    test_files = list(tests_dir.glob("test_*.py")) if tests_dir.is_dir() else []
    if not test_files:
        findings.append(
            GovernanceFinding(
                rule_id="missing_tests",
                message="No test_*.py files found in tests/",
                level=GovernanceLevel.CRITICAL,
                remediation=remediation_map["missing_tests"],
                path="tests",
            )
        )

    path_categories = repo_policy.get("path_categories", {})
    critical_meta = path_categories.get("critical_sensitive", {})
    generated_meta = path_categories.get("generated_cache", {})

    critical_patterns = repo_policy.get("critical_sensitive_paths", [])
    critical_exceptions = set(repo_policy.get("critical_sensitive_exceptions", []))
    for rel_path in list_matching_paths(repo_root, critical_patterns):
        if rel_path in critical_exceptions:
            continue
        findings.append(
            GovernanceFinding(
                rule_id=critical_meta.get("rule_id", "critical_sensitive_path_present"),
                message=f"{critical_meta.get('message_prefix', 'Critical sensitive path present')}: {rel_path}",
                level=_level_from_name(critical_meta.get("finding_level", "critical")),
                remediation=remediation_map["critical_sensitive_path_present"],
                path=rel_path,
            )
        )

    generated_patterns = repo_policy.get("generated_cache_paths", [])
    for rel_path in list_matching_paths(repo_root, generated_patterns):
        findings.append(
            GovernanceFinding(
                rule_id=generated_meta.get("rule_id", "generated_cache_path_present"),
                message=f"{generated_meta.get('message_prefix', 'Generated or cache path present')}: {rel_path}",
                level=_level_from_name(generated_meta.get("finding_level", "info")),
                remediation=remediation_map["generated_cache_path_present"],
                path=rel_path,
            )
        )

    passed = not any(item.level == GovernanceLevel.CRITICAL for item in findings)
    return DomainValidationResult(domain="repo", passed=passed, findings=findings)
