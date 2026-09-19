from typing import Any, Dict, List, Type

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from governance.models import EnforcementMode, GovernanceFinding, GovernanceLevel


class AgentEntrySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    module: str
    base_class: str
    step: str
    next_step: str
    responsibility: str


class AgentGovernanceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    description: str
    enforcement_mode: EnforcementMode = EnforcementMode.VALIDATION_ONLY
    agents: List[AgentEntrySpec]
    requirements: Dict[str, Any]
    failure_conditions: List[str]


class PipelineStageSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    agent: str | None = None


class PipelineGovernanceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    description: str
    enforcement_mode: EnforcementMode = EnforcementMode.VALIDATION_ONLY
    stages: List[PipelineStageSpec]
    shared_data_keys: Dict[str, str]
    risk_output: Dict[str, Any]
    summary_output: Dict[str, Any]
    human_review: Dict[str, Any]
    failure_conditions: List[str]


class AuditGovernanceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    description: str
    enforcement_mode: EnforcementMode = EnforcementMode.VALIDATION_ONLY
    execution_log: Dict[str, Any]
    session_state_logs: Dict[str, Any]
    session_audit_reports: Dict[str, Any]
    governance_reports: Dict[str, Any]
    ci_workflow: Dict[str, Any] = Field(default_factory=dict)
    required_evidence: List[str]
    failure_conditions: List[str]


class CiGovernanceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    description: str
    enforcement_mode: EnforcementMode = EnforcementMode.VALIDATION_ONLY
    workflow: Dict[str, Any]
    required_steps: List[str]
    commands: Dict[str, str]
    failure_policy: Dict[str, Any]
    non_goals: List[str]
    failure_conditions: List[str]


class RepoPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    description: str
    enforcement_mode: EnforcementMode = EnforcementMode.VALIDATION_ONLY
    required_files: List[str]
    required_directories: List[str]
    critical_sensitive_paths: List[str]
    critical_sensitive_exceptions: List[str] = Field(default_factory=list)
    generated_cache_paths: List[str]
    path_categories: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    tests: Dict[str, Any]
    failure_conditions: List[str]


class PolicyRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    severity: str
    check: str
    enforcement_mode: EnforcementMode = EnforcementMode.VALIDATION_ONLY


class AgentPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    description: str
    enforcement_mode: EnforcementMode = EnforcementMode.VALIDATION_ONLY
    required_agents: List[str]
    rules: List[PolicyRule]
    remediation: Dict[str, str]


class AuditPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    description: str
    enforcement_mode: EnforcementMode = EnforcementMode.VALIDATION_ONLY
    risk_findings: Dict[str, Any]
    summary: Dict[str, Any]
    audit_outputs: Dict[str, Any]
    governance_reports: Dict[str, Any]
    rules: List[PolicyRule]
    remediation: Dict[str, str]


SPEC_MODELS: Dict[str, Type[BaseModel]] = {
    "agent-governance.spec.yaml": AgentGovernanceSpec,
    "pipeline-governance.spec.yaml": PipelineGovernanceSpec,
    "audit-governance.spec.yaml": AuditGovernanceSpec,
    "ci-governance.spec.yaml": CiGovernanceSpec,
}

POLICY_MODELS: Dict[str, Type[BaseModel]] = {
    "repo_policy.yaml": RepoPolicy,
    "agent_policy.yaml": AgentPolicy,
    "audit_policy.yaml": AuditPolicy,
}


def _format_validation_error(filename: str, exc: ValidationError) -> List[GovernanceFinding]:
    findings: List[GovernanceFinding] = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", ()))
        message = error.get("msg", "Invalid value")
        findings.append(
            GovernanceFinding(
                rule_id="schema_validation_error",
                message=f"{filename} field '{location}': {message}",
                level=GovernanceLevel.CRITICAL,
                remediation=f"Fix the YAML structure in governance file {filename}",
                path=f"governance/{'specs' if filename.endswith('.spec.yaml') else 'policies'}/{filename}",
                enforcement_mode=EnforcementMode.VALIDATION_ONLY,
            )
        )
    return findings


def validate_spec_document(filename: str, document: Dict[str, Any]) -> tuple[BaseModel | None, List[GovernanceFinding]]:
    model_type = SPEC_MODELS.get(filename)
    if model_type is None:
        return None, [
            GovernanceFinding(
                rule_id="unknown_spec",
                message=f"No schema registered for spec: {filename}",
                level=GovernanceLevel.CRITICAL,
                path=f"governance/specs/{filename}",
            )
        ]
    try:
        return model_type.model_validate(document), []
    except ValidationError as exc:
        return None, _format_validation_error(filename, exc)


def validate_policy_document(filename: str, document: Dict[str, Any]) -> tuple[BaseModel | None, List[GovernanceFinding]]:
    model_type = POLICY_MODELS.get(filename)
    if model_type is None:
        return None, [
            GovernanceFinding(
                rule_id="unknown_policy",
                message=f"No schema registered for policy: {filename}",
                level=GovernanceLevel.CRITICAL,
                path=f"governance/policies/{filename}",
            )
        ]
    try:
        return model_type.model_validate(document), []
    except ValidationError as exc:
        return None, _format_validation_error(filename, exc)
