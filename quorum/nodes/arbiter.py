"""Arbiter node for deciding whether a query result is accepted or retried."""

import asyncio
import json
import os
from pathlib import Path

from quorum.llm import AnthropicLLMClient
from quorum.schemas.critique import ArbitrationResult, CritiqueResult
from quorum.state import AgentState

CLAUDE_OPUS_MODEL = "claude-opus-4-6"
LOW_CONFIDENCE_APPROVAL_THRESHOLD = 0.70

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "arbiter.txt"
ARBITER_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")

claude_opus_client = AnthropicLLMClient(
    api_key=os.getenv("ANTHROPIC_API_KEY", "missing-anthropic-api-key")
)


def arbiter(state: AgentState) -> dict[str, ArbitrationResult]:
    """Arbitrate the three critic results and return only the arbitration update."""
    critiques = _normalized_critiques(state)
    avg_confidence = sum(critique.confidence_score for critique in critiques) / 3
    vote_summary = {
        critique.critic_id: critique.approved for critique in critiques
    }

    arbitration = asyncio.run(
        claude_opus_client.call_llm(
            system_prompt=ARBITER_PROMPT,
            user_prompt=_build_arbiter_user_prompt(
                state=state,
                critiques=critiques,
                avg_confidence=avg_confidence,
            ),
            response_model=ArbitrationResult,
            model_string=CLAUDE_OPUS_MODEL,
        )
    )

    final_approved = arbitration.final_approved
    if all(vote_summary.values()) and avg_confidence < LOW_CONFIDENCE_APPROVAL_THRESHOLD:
        final_approved = False
    if state.attempts >= state.max_attempts:
        final_approved = True

    arbitration = ArbitrationResult(
        **{
            **arbitration.model_dump(),
            "step_number": _step_number(state),
            "vote_summary": vote_summary,
            "avg_confidence": avg_confidence,
            "final_approved": final_approved,
        }
    )

    return {"arbitration": arbitration}


def _normalized_critiques(state: AgentState) -> list[CritiqueResult]:
    step_number = _step_number(state)
    return [
        state.critique_openai
        or _missing_critique(critic_id="openai", step_number=step_number),
        state.critique_gemini
        or _missing_critique(critic_id="gemini", step_number=step_number),
        state.critique_deepseek
        or _missing_critique(critic_id="deepseek", step_number=step_number),
    ]


def _missing_critique(*, critic_id: str, step_number: int) -> CritiqueResult:
    return CritiqueResult(
        critic_id=critic_id,
        step_number=step_number,
        approved=False,
        confidence_score=0.0,
        issues_found=[f"{critic_id} critique missing"],
        suggested_correction="Rerun the missing critic before accepting the result.",
        reasoning="This critic did not return a critique and is treated as a rejection.",
    )


def _build_arbiter_user_prompt(
    *,
    state: AgentState,
    critiques: list[CritiqueResult],
    avg_confidence: float,
) -> str:
    return f"""Current QueryStep objective:
{_step_objective(state)}

Attempt number and max attempts:
{state.attempts} of {state.max_attempts}

OpenAI critique:
{critiques[0].model_dump_json()}

Gemini critique:
{critiques[1].model_dump_json()}

DeepSeek critique:
{critiques[2].model_dump_json()}

avg_confidence calculated by Python:
{json.dumps(avg_confidence)}
"""


def _step_number(state: AgentState) -> int:
    if state.query_plan is not None:
        try:
            return state.query_plan.steps[state.current_step_index].step_number
        except IndexError:
            pass
    if state.query_result is not None:
        return state.query_result.step_number
    if state.validated_query is not None:
        return state.validated_query.step_number
    return state.current_step_index + 1


def _step_objective(state: AgentState) -> str:
    if state.query_plan is None:
        return "No query plan available."
    try:
        return state.query_plan.steps[state.current_step_index].objective
    except IndexError:
        return "Current step index is outside the query plan."
