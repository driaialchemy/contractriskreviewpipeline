from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class GovernanceLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class EnforcementMode(str, Enum):
    VALIDATION_ONLY = "validation_only"
    ENFORCEMENT_READY = "enforcement_ready"
    EXECUTION_BLOCKING = "execution_blocking"


class GovernanceFinding(BaseModel):
    rule_id: str
    message: str
    level: GovernanceLevel
    remediation: Optional[str] = None
    path: Optional[str] = None
    enforcement_mode: EnforcementMode = EnforcementMode.VALIDATION_ONLY


class DomainValidationResult(BaseModel):
    domain: str
    passed: bool
    findings: List[GovernanceFinding] = Field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for item in self.findings if item.level == GovernanceLevel.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for item in self.findings if item.level == GovernanceLevel.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for item in self.findings if item.level == GovernanceLevel.INFO)


class GovernanceReport(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    overall_status: str = "pass"
    risk_level: str = "low"
    exit_code: int = 0
    exit_behavior: str = "Exit 0 unless critical findings exist; warnings and info do not fail validation."
    default_enforcement_mode: str = EnforcementMode.VALIDATION_ONLY.value
    repo_validation: DomainValidationResult
    spec_validation: DomainValidationResult
    policy_validation: DomainValidationResult
    agent_validation: DomainValidationResult
    pipeline_validation: DomainValidationResult
    audit_validation: DomainValidationResult
    evidence_paths: List[str] = Field(default_factory=list)
    known_limitations: List[str] = Field(default_factory=list)

    @property
    def all_findings(self) -> List[GovernanceFinding]:
        domains = [
            self.repo_validation,
            self.spec_validation,
            self.policy_validation,
            self.agent_validation,
            self.pipeline_validation,
            self.audit_validation,
        ]
        findings: List[GovernanceFinding] = []
        for domain in domains:
            findings.extend(domain.findings)
        return findings

    @property
    def failures(self) -> List[GovernanceFinding]:
        return [item for item in self.all_findings if item.level == GovernanceLevel.CRITICAL]

    @property
    def warnings(self) -> List[GovernanceFinding]:
        return [item for item in self.all_findings if item.level == GovernanceLevel.WARNING]

    @property
    def infos(self) -> List[GovernanceFinding]:
        return [item for item in self.all_findings if item.level == GovernanceLevel.INFO]

    @property
    def severity_counts(self) -> dict[str, int]:
        return {
            "critical": len(self.failures),
            "warning": len(self.warnings),
            "info": len(self.infos),
        }

    def compute_overall_status(self) -> None:
        if self.failures:
            self.overall_status = "fail"
            self.risk_level = "critical"
            self.exit_code = 1
        elif self.warnings:
            self.overall_status = "pass_with_warnings"
            self.risk_level = "medium"
            self.exit_code = 0
        else:
            self.overall_status = "pass"
            self.risk_level = "low"
            self.exit_code = 0

    @staticmethod
    def default_known_limitations() -> List[str]:
        return [
            "AST-based agent validation checks static class patterns only.",
            "Dynamic agent registration or monkey-patching is not validated.",
            "Dataset availability is runtime configuration (CUAD_DATASET_ZIP) and not required for governance validation.",
            "CI branch triggers are configured for main/master; adjust .github/workflows/governance.yml for other default branches.",
            "Governance rules default to validation_only; they report conformance and do not stop the CUAD pipeline at runtime except via CI/CLI exit on critical failures.",
            "High/critical contract findings require human_review_status but do not prevent summary generation in the current pipeline.",
        ]
