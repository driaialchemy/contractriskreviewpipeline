from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field

class ClauseExtraction(BaseModel):
    clause_type: str
    extracted_text: str
    is_impossible: bool
    answer_start: Optional[int] = None
    question_id: str

class RiskFlag(BaseModel):
    clause_type: str
    severity: str        # "critical", "high", "medium", "low", "none"
    deviation: str
    playbook_standard: str
    extracted_value: str
    recommendation: str
    human_review_status: str = "not_required"  # "required" for critical/high findings
    reasoning_path: Optional[List[str]] = None
    policy_matched: Optional[str] = None  # canonical: policy id; see governance-logger/docs/decision-lineage-schema.md
    confidence: Optional[float] = None

class ValidationResult(BaseModel):
    clause_type: str
    ground_truth_text: str
    agent_extracted_text: str
    match: bool
    match_score: float   # 0.0 to 1.0, simple overlap ratio

class StepExecutionTrace(BaseModel):
    agent_name: str
    step_name: str
    sequence_number: int
    status: str = "success"
    started_at: datetime
    completed_at: datetime
    duration_ms: float
    timestamp: datetime
    error_message: Optional[str] = None
    input_received: Dict[str, Any]
    agent_rationale: str
    output_generated: Dict[str, Any]

class AgentState(BaseModel):
    session_id: str
    contract_title: str
    current_step: str = "extraction"
    shared_data: Dict[str, Any] = Field(default_factory=dict)
    execution_traces: List[StepExecutionTrace] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
