import asyncio
from pathlib import Path
from typing import Any, Dict, List

import yaml

from governance.models import DomainValidationResult, GovernanceFinding, GovernanceLevel
from governance.schemas import (
    POLICY_MODELS,
    SPEC_MODELS,
    validate_policy_document,
    validate_spec_document,
)

GOVERNANCE_ROOT = Path(__file__).resolve().parent.parent
SPECS_DIR = GOVERNANCE_ROOT / "specs"
POLICIES_DIR = GOVERNANCE_ROOT / "policies"

SPEC_FILES = list(SPEC_MODELS.keys())
POLICY_FILES = list(POLICY_MODELS.keys())


def _read_yaml(path: Path) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected mapping in {path}")
    return loaded


async def load_yaml_file(path: Path) -> Dict[str, Any]:
    return await asyncio.to_thread(_read_yaml, path)


async def load_specs() -> Dict[str, Dict[str, Any]]:
    specs: Dict[str, Dict[str, Any]] = {}
    for filename in SPEC_FILES:
        path = SPECS_DIR / filename
        specs[filename] = await load_yaml_file(path)
    return specs


async def load_policies() -> Dict[str, Dict[str, Any]]:
    policies: Dict[str, Dict[str, Any]] = {}
    for filename in POLICY_FILES:
        path = POLICIES_DIR / filename
        policies[filename] = await load_yaml_file(path)
    return policies


def validate_spec_schemas(specs: Dict[str, Dict[str, Any]]) -> DomainValidationResult:
    findings: List[GovernanceFinding] = []
    for filename in SPEC_FILES:
        document = specs.get(filename)
        if document is None:
            findings.append(
                GovernanceFinding(
                    rule_id="missing_spec",
                    message=f"Governance spec not loaded: {filename}",
                    level=GovernanceLevel.CRITICAL,
                    remediation="Restore the missing governance spec file",
                    path=f"governance/specs/{filename}",
                )
            )
            continue
        _, schema_findings = validate_spec_document(filename, document)
        findings.extend(schema_findings)

    passed = not any(item.level == GovernanceLevel.CRITICAL for item in findings)
    return DomainValidationResult(domain="spec", passed=passed, findings=findings)


def validate_policy_schemas(policies: Dict[str, Dict[str, Any]]) -> DomainValidationResult:
    findings: List[GovernanceFinding] = []
    for filename in POLICY_FILES:
        document = policies.get(filename)
        if document is None:
            findings.append(
                GovernanceFinding(
                    rule_id="missing_policy",
                    message=f"Governance policy not loaded: {filename}",
                    level=GovernanceLevel.CRITICAL,
                    remediation="Restore the missing governance policy file",
                    path=f"governance/policies/{filename}",
                )
            )
            continue
        _, schema_findings = validate_policy_document(filename, document)
        findings.extend(schema_findings)

    passed = not any(item.level == GovernanceLevel.CRITICAL for item in findings)
    return DomainValidationResult(domain="policy", passed=passed, findings=findings)


def resolve_repo_root(start: Path | None = None) -> Path:
    if start is None:
        start = Path(__file__).resolve()
    current = start if start.is_dir() else start.parent
    for candidate in [current, *current.parents]:
        if (candidate / "main.py").exists() and (candidate / "governance").is_dir():
            return candidate
    return Path(__file__).resolve().parent.parent.parent


def list_matching_paths(repo_root: Path, patterns: List[str]) -> List[str]:
    matches: List[str] = []
    for pattern in patterns:
        normalized = pattern.replace("\\", "/")
        if normalized.endswith("/"):
            target = repo_root / normalized.rstrip("/")
            if target.is_dir():
                matches.append(normalized.rstrip("/"))
            continue
        for path in repo_root.glob(normalized):
            rel = path.relative_to(repo_root).as_posix()
            matches.append(rel)
    return sorted(set(matches))
