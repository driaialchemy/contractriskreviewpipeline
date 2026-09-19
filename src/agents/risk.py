import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.orchestrator.state import AgentState, ClauseExtraction, RiskFlag

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PLAYBOOK_PATH = PROJECT_ROOT / "data" / "playbook.json"

SEVERITY_ORDER = ["critical", "high", "medium", "low", "none"]
HUMAN_REVIEW_SEVERITIES = {"critical", "high"}


def _human_review_status(severity: str) -> str:
    return "required" if severity in HUMAN_REVIEW_SEVERITIES else "not_required"


def _lineage_fields(
    clause_type: str,
    playbook_entry: Dict[str, Any],
    path: List[str],
    confidence: float,
) -> Dict[str, Any]:
    return {
        "reasoning_path": path,
        "policy_matched": clause_type,
        "confidence": confidence,
    }


def _make_risk_flag(**kwargs: Any) -> RiskFlag:
    severity = str(kwargs["severity"])
    kwargs["human_review_status"] = _human_review_status(severity)
    return RiskFlag(**kwargs)


def _load_playbook() -> Dict[str, Any]:
    with open(PLAYBOOK_PATH, encoding="utf-8") as playbook_file:
        return json.load(playbook_file)


def _find_extraction(
    extractions: List[ClauseExtraction], clause_type: str
) -> Optional[ClauseExtraction]:
    for extraction in extractions:
        if extraction.clause_type == clause_type:
            return extraction
    return None


def _evaluate_clause_risk(
    clause_type: str,
    playbook_entry: Dict[str, Any],
    extraction: Optional[ClauseExtraction],
) -> RiskFlag:
    standard = playbook_entry.get("standard", "")
    extracted_value = ""
    is_missing = extraction is None or extraction.is_impossible
    is_ambiguous = False

    if extraction is not None:
        extracted_value = extraction.extracted_text
        if not extraction.is_impossible and len(extraction.extracted_text.strip()) < 20:
            is_ambiguous = True

    if clause_type == "Uncapped Liability" and extraction is not None and not extraction.is_impossible:
        severity = playbook_entry.get("risk_if_present", "critical")
        recommendation = playbook_entry.get(
            "recommendation_if_present",
            "Reject or renegotiate — uncapped liability is critical risk",
        )
        return _make_risk_flag(
            clause_type=clause_type,
            severity=severity,
            deviation="Uncapped liability clause detected in contract",
            playbook_standard=standard,
            extracted_value=extracted_value,
            recommendation=recommendation,
            **_lineage_fields(
                clause_type,
                playbook_entry,
                ["load_playbook", "detect_uncapped_liability", f"severity:{severity}"],
                0.9,
            ),
        )

    if is_missing:
        severity = playbook_entry.get("risk_if_missing", "medium")
        recommendation = playbook_entry.get(
            "recommendation_if_missing",
            f"Address missing {clause_type} clause",
        )
        return _make_risk_flag(
            clause_type=clause_type,
            severity=severity,
            deviation=f"{clause_type} clause is absent from contract",
            playbook_standard=standard,
            extracted_value="",
            recommendation=recommendation,
            **_lineage_fields(
                clause_type,
                playbook_entry,
                ["load_playbook", "clause_missing", f"risk_if_missing:{severity}"],
                0.95,
            ),
        )

    if is_ambiguous:
        severity = playbook_entry.get("risk_if_ambiguous", "medium")
        recommendation = playbook_entry.get(
            "recommendation_if_missing",
            f"Clarify ambiguous {clause_type} language",
        )
        return _make_risk_flag(
            clause_type=clause_type,
            severity=severity,
            deviation=f"{clause_type} clause present but text is ambiguous or too short",
            playbook_standard=standard,
            extracted_value=extracted_value,
            recommendation=recommendation,
            **_lineage_fields(
                clause_type,
                playbook_entry,
                ["load_playbook", "clause_ambiguous", f"risk_if_ambiguous:{severity}"],
                0.55,
            ),
        )

    return _make_risk_flag(
        clause_type=clause_type,
        severity="none",
        deviation="Clause present and appears standard",
        playbook_standard=standard,
        extracted_value=extracted_value,
        recommendation="No action required",
        **_lineage_fields(
            clause_type,
            playbook_entry,
            ["load_playbook", "clause_present", "appears_standard"],
            0.85,
        ),
    )


def _compute_overall_severity(flags: List[RiskFlag]) -> str:
    for severity in SEVERITY_ORDER:
        if any(flag.severity == severity for flag in flags):
            return severity
    return "none"


def _build_risk_summary(flags: List[RiskFlag]) -> Dict[str, Any]:
    non_none_flags = [flag for flag in flags if flag.severity != "none"]
    summary = {
        "total_flags": len(non_none_flags),
        "critical_count": sum(1 for flag in flags if flag.severity == "critical"),
        "high_count": sum(1 for flag in flags if flag.severity == "high"),
        "medium_count": sum(1 for flag in flags if flag.severity == "medium"),
        "low_count": sum(1 for flag in flags if flag.severity == "low"),
        "overall_severity": _compute_overall_severity(flags),
    }
    return summary


class RiskAgent(BaseAgent):
    """Compares extracted clauses against the legal playbook and assigns risk severity."""

    name = "RiskAgent"

    async def process(self, state: AgentState) -> AgentState:
        if state.current_step != "risk_assessment":
            return state

        input_received = {
            "extractions_count": len(state.shared_data.get("extractions", [])),
            "current_step": state.current_step,
        }

        try:
            started_at, start_perf = self.start_trace_timing()
            playbook = await asyncio.to_thread(_load_playbook)
            raw_extractions = state.shared_data.get("extractions", [])
            extractions = [ClauseExtraction.model_validate(item) for item in raw_extractions]

            risk_flags: List[RiskFlag] = []
            for clause_type, playbook_entry in playbook.items():
                extraction = _find_extraction(extractions, clause_type)
                risk_flags.append(
                    _evaluate_clause_risk(clause_type, playbook_entry, extraction)
                )

            risk_summary = _build_risk_summary(risk_flags)

            state.shared_data["risk_flags"] = [flag.model_dump() for flag in risk_flags]
            state.shared_data["risk_summary"] = risk_summary

            rationale = (
                f"Assessed {len(risk_flags)} playbook clauses: "
                f"{risk_summary['critical_count']} critical, "
                f"{risk_summary['high_count']} high, "
                f"{risk_summary['medium_count']} medium, "
                f"{risk_summary['low_count']} low flags. "
                f"Highest severity: {risk_summary['overall_severity']}."
            )
            output = {
                "total_flags": risk_summary["total_flags"],
                "overall_severity": risk_summary["overall_severity"],
            }
            self.log_trace(
                state,
                input_received,
                rationale,
                output,
                step_name="risk_assessment",
                sequence_number=2,
                started_at=started_at,
                start_perf=start_perf,
            )
            state.current_step = "advisory"

        except Exception as exc:
            state.errors.append(f"RiskAgent error: {exc}")

        return state
