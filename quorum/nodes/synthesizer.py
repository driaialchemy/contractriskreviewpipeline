"""Synthesizer node for producing the final insight report."""

import asyncio
import json
import os
from pathlib import Path

from quorum.llm import AnthropicLLMClient
from quorum.schemas.report import InsightReport
from quorum.state import AgentState

CLAUDE_SONNET_MODEL = "claude-sonnet-4-6"
MODELS_USED = [
    "claude-sonnet-4-6",
    "gpt-5.5-2026-04-23",
    "gemini-3.1-pro-preview",
    "deepseek-v4-pro",
    "claude-opus-4-6",
]
MANDATORY_CAVEATS = [
    "Analysis uses TPC-H sample data, not production business data.",
    "SQL row limits cap returned data at 100 rows, so rankings or examples may be truncated.",
    "Multi-model critique flags improve review coverage but do not guarantee correctness.",
]

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "synthesizer.txt"
SYNTHESIZER_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")

claude_client = AnthropicLLMClient(
    api_key=os.getenv("ANTHROPIC_API_KEY", "missing-anthropic-api-key")
)


def synthesizer(state: AgentState) -> dict[str, InsightReport | str]:
    """Synthesize approved query results into a final insight report."""
    ensemble_summary = list(state.arbitration_history)
    if state.arbitration is not None:
        ensemble_summary.append(state.arbitration)

    if not state.all_results:
        return {
            "insight_report": _empty_results_report(
                state=state,
                ensemble_summary=ensemble_summary,
            ),
            "status": "failed",
        }

    report = asyncio.run(
        claude_client.call_llm(
            system_prompt=SYNTHESIZER_PROMPT,
            user_prompt=_build_synthesizer_user_prompt(state),
            response_model=InsightReport,
            model_string=CLAUDE_SONNET_MODEL,
        )
    )

    report = InsightReport(
        **{
            **report.model_dump(),
            "original_question": state.question,
            "data_tables": state.all_results,
            "ensemble_summary": ensemble_summary,
            "total_attempts": _total_attempts(state),
            "steps_executed": len(state.all_results),
            "models_used": MODELS_USED,
            "caveats": _merge_mandatory_caveats(report.caveats),
        }
    )

    return {"insight_report": report, "status": "complete"}


def _empty_results_report(
    *,
    state: AgentState,
    ensemble_summary: list,
) -> InsightReport:
    return InsightReport(
        original_question=state.question,
        executive_summary=(
            "Quorum could not produce an approved result for this question. "
            "No business conclusion was generated because every available query path failed review or execution."
        ),
        key_findings=[],
        data_tables=[],
        caveats=_merge_mandatory_caveats(
            [
                "No query result was approved within the retry limit.",
            ]
        ),
        ensemble_summary=ensemble_summary,
        total_attempts=_total_attempts(state),
        steps_executed=0,
        models_used=MODELS_USED,
    )


def _build_synthesizer_user_prompt(state: AgentState) -> str:
    return f"""Original question:
{state.question}

Query plan summary:
{_query_plan_summary(state)}

Approved query results:
{json.dumps([_result_summary(result) for result in state.all_results], default=str)}

Arbitration decisions:
{json.dumps(
    [state.arbitration.model_dump()] if state.arbitration is not None else [],
    default=str,
)}

Total attempts and steps executed:
{_total_attempts(state)} attempts across {len(state.all_results)} approved steps
"""


def _query_plan_summary(state: AgentState) -> str:
    if state.query_plan is None:
        return "No query plan available."
    return state.query_plan.model_dump_json()


def _result_summary(result) -> dict:
    return {
        "step_number": result.step_number,
        "sql_executed": result.sql_executed,
        "columns": result.columns,
        "row_count": result.row_count,
        "first_10_rows": result.rows[:10],
        "success": result.success,
        "error_detail": result.error_detail,
    }


def _merge_mandatory_caveats(existing_caveats: list[str]) -> list[str]:
    caveats = list(existing_caveats)
    for caveat in MANDATORY_CAVEATS:
        if caveat not in caveats:
            caveats.append(caveat)
    return caveats


def _total_attempts(state: AgentState) -> int:
    return max(state.attempts, len(state.all_results))
